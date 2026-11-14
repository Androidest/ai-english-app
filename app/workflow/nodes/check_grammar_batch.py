from langgraph.runtime import Runtime
from langgraph.types import Send
from app.workflow.schema_handlers.commons import item_to_text

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schema_handlers.issue_batch_handler import (
    validate_issue_batch_uids,
    validate_batch_reasons,
)

SYS_PROMPT_TEMPLATE = """You are an expert content grammar checker.
Identify only the sentences with grammar errors. Do NOT repair them.

Hard requirements:
- Return only the issue entries for problematic sentences.
- Each issue must include its UID and a short reason describing the grammatical error.
- Each reason description should be in one line. DO NOT SPLIT them into multiple lines.
- Each reasons shall be compact and precise.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured issue data. Do not add extra explanations, commentary, or preamble.
- Omit entries where the sentence is grammatically correct.
- Do not return any repaired sentence text.
- Return `issues` as an EMPTY list if all sentences are grammatically correct.
- The issues should consider preserving the following whenever possible from the original text:
    1. Tone
    2. Vocabulary difficulty level
    3. Semantic intent
    8. Wording style

Target language:
{language}

Inspect the following {language} sentences for grammatical issues:
{batch_sentences}
"""


def fanout_check_grammar_batch(
    node: str,
    state: LessonGeneratorState,
) -> list[Send]:
    
    """
    To fan-out the 'check_grammar_batch' node into many parallel nodes to process all the batches.
    args:
        node: 
            The name of the target node to fan-out.
        batched:
            The target batches for grammar checking. It's dictionary with batch ID as the key, batch as the value.
        language:
            The language of the sentences of the supplied batches.
    """

    req = state["issue_correction_request"]
    batches = state[req.target_batches_key]
    batch_ids = state['processing_batch_ids']

    return [
        Send(
            node=node,
            arg=ParallelBatchState(
                batch_id=id,
                batch=batches[id],
                main_state=state,
            )  # local state
        )
        for id in batch_ids
    ]


def check_grammar_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """
    Node: Check the batch and report only problematic sentences with UID and reason.
    """

    batch_id = state["batch_id"]
    batch = state["batch"]
    language = state["main_state"]["issue_correction_request"].language

    uids_batch = set(item.uid for item in batch.items)
    sentence_batch_txt = item_to_text(batch)

    def verify_cb(o: IssueBatch):

        if len(o.issues) == 0:
            return  # nothing is problematic

        ok, reason = validate_issue_batch_uids(
            expected_uids=uids_batch,
            actual_batch=o,
            check_missing=False,
        )

        if not ok:
            raise Exception(reason)

        ok, reason = validate_batch_reasons(
            batch=o,
        )

        if not ok:
            raise Exception(reason)

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.0, # recommended temperature for grammar checking.
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=IssueBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=False,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        language=language,
        batch_sentences=sentence_batch_txt,
    )

    result: IssueBatch = llm.invoke(
        input=sys_prompt,
    )

    issue_batches = { batch_id: result } if result.issues else {}

    return {
        "issue_batches": issue_batches,
    }