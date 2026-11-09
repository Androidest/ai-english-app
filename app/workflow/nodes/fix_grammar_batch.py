from langgraph.runtime import Runtime
from langgraph.types import Send
import warnings

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_sentence_batch_uids,
    validate_batch_sentence,
    merge_batch,
)

SYS_PROMPT_TEMPLATE = """You are an expert {language} content grammar fixer.
Repair only the sentences listed below. Each sentence comes with a reason describing its grammar error.

Hard requirements:
- Fix only the grammar error described in the repair reason for each sentence. Do not make unrelated changes.
- Treat the UIDs as keys only and preserve them exactly as supplied. Never create, delete, rename, or modify an UID.
- Generate exactly one repaired sentence per UID.
- Do not directly copy the supplied sentences. Modify them per their repair reasons.
- Return only structured output. Do not add explanations or commentary.
- Preserve all of the following whenever possible from the original text:
    1. Tone
    2. Vocabulary difficulty level
    3. Sentence length
    4. Semantic intent

Target language:
{language}

Sentences to repair (with repair reasons):
{items_to_fix}

Return only the repaired items.
"""

ISSUE_TEMPLATE = """
* UID: '{uid}'
* Sentence: '{sentence}'
* Repair reason: '{reason}'
--------------"""

COPY_ERROR_TEMPLATE = """The following uids were returned with text identical to the original:
{uids}

You should fix the grammar error for these uids according to their reasons.
These sentences should be modified, not copied.
"""


def fanout_fix_grammar_batch(
    node: str,
    state: LessonGeneratorState,
) -> list[Send]:
    
    """
    To fan-out the 'fix_grammar_batch' node into many parallel nodes to process all the batches.
    args:
        node: 
            The name of the target node to fan-out.
        batched:
            The target batches for grammar fixing. It's dictionary with batch ID as the key, batch as the value.
        language:
            The language of the sentences of the supplied batches.
    """

    req = state["issue_correction_request"]
    batches = state[req.target_batches_key]
    batch_ids = state["issue_batches"].keys()

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


def _build_items_to_fix(
    batch: SentenceBatch, 
    issue_batch: IssueBatch,
) -> str:

    """
    Build the repair payload: only sentences with reported issues, each with its reason.
    """

    reason_by_uid = {issue.uid: issue.reason for issue in issue_batch.issues}
    items = [
        ISSUE_TEMPLATE.format(
            uid=item.uid,
            sentence=item.val,
            reason=reason_by_uid[item.uid],
        )
        for item in batch.items
        if item.uid in reason_by_uid
    ]
    text = "".join(items)
    print(text)
    return text


def fix_grammar_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """
    Node: Repair only the sentences flagged by the check node.
    """

    batch_id = state["batch_id"]
    batch = state["batch"]
    main_state = state["main_state"]
    issue_batch = main_state["issue_batches"][batch_id]
    language = main_state["issue_correction_request"].language

    if len(issue_batch.issues) == 0:
        return LessonGeneratorState(corrected_batches={})

    uids_batch = set(issue.uid for issue in issue_batch.issues)
    items_to_fix_txt = _build_items_to_fix(batch, issue_batch)

    def verify_cb(o: SentenceBatch):

        if len(o.items) == 0:
            raise Exception("Expected repaired items, got empty list.")

        ok, reason = validate_sentence_batch_uids(
            expected_uids=uids_batch,
            actual_batch=o,
            check_missing=False,
        )

        if not ok:
            raise Exception(reason)

        ok, reason = validate_batch_sentence(
            batch=o,
            max_len=999,
            prompt_max_len=999,
        )

        error_uids = []
        sent_by_id = { item.uid: item.val for item in o.items }
        for item in batch.items:
            if item.uid in sent_by_id and sent_by_id[item.uid] == item.val:
                error_uids.append(f'- uid="{item.uid}"')

        if error_uids:
            warnings.warn(f"[fix_grammar_batch] Repeating sentences: {[ item.uid for item in o.items ]}")
            raise Exception(COPY_ERROR_TEMPLATE.format(uids="\n".join(error_uids)))

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.3, # recommended temperature for grammar repair
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=SentenceBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        language=language,
        items_to_fix=items_to_fix_txt,
    )

    result: SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    merged_batch = merge_batch(
        base=batch,
        updates=result,
    )

    # if result.items:
    #     print("------------ After Repair ---------------")
    #     print(result.model_dump_json(indent=2, ensure_ascii=False))

    return LessonGeneratorState(
        corrected_batches={ batch_id: merged_batch },
    )