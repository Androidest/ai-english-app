from langgraph.runtime import Runtime
from langgraph.types import Send
from app.workflow.schema_handlers.commons import item_to_text

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schema_handlers.commons import normalize_text
from app.workflow.schema_handlers.issue_batch_handler import (
    validate_issue_batch_uids,
    validate_batch_reasons,
)

SYS_PROMPT_TEMPLATE = """You are an expert translation and grammar checker.
Identify only the sentences with translation and grammar issues. Do NOT repair them.

Hard requirements:
- Return only issue entries for problematic translations.
- Each issue must include only the UID and a reason thoroughly describing both the translation and grammatical issues in the translation.
- Each reason description should be in one line. DO NOT SPLIT them into multiple lines.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured issue data. Do not add extra explanations, commentary, or preamble.
- Omit entries where the translation is correct and has no grammatical issues.
- Do not return the translated source text or any repaired sentence text.
- Return `issues` as an EMPTY list if all translations are correct.
- The language of the reason must match the translation language.
- [Top priority] Verify that each translated sentence closely aligns with its source sentence on all of the following:
    1. Semantic intent
    2. The original meaning
    3. Negation
    4. Tense/aspect meaning
    5. Modality
    6. Numbers and quantities
    7. Dates and times
    8. Names and named entities
    9. Tone
    10. Causal relationship
    11. Wording style
- Check whether the translations satisfy all of the following:
    1. No meaningful information from the source is omitted.
    2. No extra information not present in the source is added.
    3. The translation reads naturally and smoothly.
    4. The translation does not deviate from the original intent.
- [IMPORTANT] When inspecting issues, use the logic and expression of the source sentence as the baseline for evaluation. 
    Even if the source sentence contains errors, 
    do not flag those inherent source errors as translation or grammatical issues of the target text.

Source Language:
{src_language}

Translation language:
{language}

Inspect the following {src_language}-{language} pairs for {language} translation and grammatical issues:
{batch_pairs}
"""


def fanout_check_translation_batch(
    node: str,
    state: LessonGeneratorState,
) -> list[Send]:
    
    """
    To fan-out the 'check_translation_batch' node into many parallel nodes to process all the batches.
    args:
        node: 
            The name of the target node to fan-out.
        batched:
            The target batches for translation checking. It's dictionary with batch ID as the key, batch as the value.
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


def _build_batch_pair_txt(
    src_batch: SentenceBatch, 
    trans_batch: SentenceBatch,
) -> str:

    """
    Build the checking payload: 
    Each line contains one source-translation sentence pair followed by an UID.
    """

    uid_src_map = { item.uid: item.val for item in src_batch.items }
    pairs = [
        {
            "uid": item.uid,
            "source": normalize_text(uid_src_map[item.uid]),
            "trans": normalize_text(item.val)
        }
        for item in trans_batch.items
    ]
    text = item_to_text(pairs)
    return text


def check_translation_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """
    Node: Check the batch and report only problematic sentences with UID and reason.
    """

    main_state = state["main_state"]
    req = main_state["issue_correction_request"]
    batch_id = state["batch_id"]
    src_batch = main_state["src_batches"][batch_id]
    trans_batch = state["batch"]
    source_language = req.source_language
    language = req.language

    uids_batch = set(item.uid for item in trans_batch.items)
    batch_pairs_txt = _build_batch_pair_txt(src_batch, trans_batch)

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
        temperature=0.0, # recommended temperature for translation checking.
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=IssueBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=False,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        src_language=source_language,
        language=language,
        batch_pairs=batch_pairs_txt,
    )

    result: IssueBatch = llm.invoke(
        input=sys_prompt,
    )

    issue_batches = { batch_id: result } if result.issues else {}

    return {
        "issue_batches": issue_batches,
    }