from langgraph.runtime import Runtime
from langgraph.types import Send
import warnings
from app.workflow.schema_handlers.commons import item_to_text

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schema_handlers.commons import normalize_text
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_sentence_batch_uids,
    validate_batch_sentence,
)

SYS_PROMPT_TEMPLATE = """You are an expert grammar and translation corrector.
Each entry includes a UID, source sentence, current translation, repair reason, and optional previous_trans.
Repair only substantive defects identified by the repair reason.

Input fields per entry:
- uid: the key.
- source: the source sentence.
- trans: the current translation (output of the previous repair round, or the original translation on the first round).
- reason: the defect reported for `trans`.
- previous_trans (optional): the original translation or the translation produced by the PREVIOUS repair round for this same uid. Absent on the first round.

How to use previous_trans:
- If previous_trans is absent: treat `trans` as the original translation and repair normally.
- If `reason` describes a DIFFERENT substantive defect not addressed by the previous change, repair it.
- If `reason` is a synonym/style/elegance preference, or asks to revert/contradict the direction of the previous translation (oscillation, e.g. "use A" then "use B" then "use A"), return `trans` UNCHANGED as the current repaired translation for that UID.
- If `reason` restates the SAME defect that previous_trans already attempted to fix and the current text is a reasonable faithful rendering, return `trans` UNCHANGED as the current repaired translation for that UID.

Hard requirements:
- Generate exactly one output sentence per UID.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured repaired data. Do not add extra explanations, commentary, or preamble.
- Fix only the substantive defect described in the repair reason. Do not make unrelated style, synonym, or elegance changes.
- Do not repair or output the source sentences. Only the translation may be modified.
- Do not omit meaningful information from the source.
- Do not add information that does not exist in the source.
- Do not copy directly from the source sentence. Returning the current translation unchanged is allowed only under the skip condition above.
- Preserve all of the following from the source:
  1. Numbers and quantities
  2. Dates and times
  3. Names and named entities

Source Language:
{src_language}

Translation language:
{language}

Items to repair:
{items_to_fix}

Now output the updated translations.
"""


def fanout_fix_translation_batch(
    node: str,
    state: LessonGeneratorState,
) -> list[Send]:
    
    """
    To fan-out the 'fix_translation_batch' node into many parallel nodes to process all the batches.
    args:
        node: 
            The name of the target node to fan-out.
        batched:
            The target batches for grammar fixing. It's dictionary with batch ID as the key, batch as the value.
        language:
            The language of the sentences of the supplied batches.
    """

    batches = state["processing_batches"]
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
    src_batch: SentenceBatch, 
    trans_batch: SentenceBatch,
    issue_batch: IssueBatch,
    previous_trans_batch: dict[str, str],
    output_batch: SentenceBatch = None, # for testing
) -> str:

    """
    Build the repair payload: 
    Each line contains one source-translation sentence pair 
    followed by an UID and a repair reason.
    """

    uid_issue_map = { item.uid: item.reason for item in issue_batch.issues }
    uid_trans_map = { item.uid: item.val for item in trans_batch.items if item.uid in uid_issue_map}
    if output_batch:
        uid_out_map = { item.uid: item.val for item in output_batch.items }

    items = []
    for item in src_batch.items:
        if item.uid in uid_issue_map:
            new_item = {
                "uid": item.uid,
                "source": normalize_text(item.val),
                "trans": normalize_text(uid_trans_map[item.uid]),
                "reason": normalize_text(uid_issue_map[item.uid]),
            }

            if previous_trans_batch:
                new_item["previous_trans"] = normalize_text(previous_trans_batch[item.uid]),
            
            if output_batch:
                new_item["repaired"] = normalize_text(uid_out_map[item.uid])

            items.append(new_item)

    text = item_to_text(items)
    return text


def fix_translation_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """
    Node: Repair only the sentences flagged by the check node.
    """

    main_state = state["main_state"]
    req = main_state["issue_correction_request"]
    batch_id = state["batch_id"]
    attemps = req.max_attempts - main_state["remaining_attempts"] + 1

    src_batch = main_state["src_batches"][batch_id]
    trans_batch = state["batch"]
    issue_batch = main_state["issue_batches"][batch_id]
    pre_corrected_batches = main_state["pre_corrected_batches"]
    previous_trans_batch = None

    if len(pre_corrected_batches) > 0:
        previous_trans_batch = pre_corrected_batches[batch_id]

    source_language = req.source_language
    language = req.language
    
    if len(issue_batch.issues) == 0:
        return {
            "corrected_batches": {}
        }

    uids_batch = set(issue.uid for issue in issue_batch.issues)
    items_to_fix_txt = _build_items_to_fix(src_batch, trans_batch, issue_batch, previous_trans_batch)

    def verify_cb(o: SentenceBatch):

        if len(o.items) == 0:
            raise Exception("Expected repaired items, got empty list.")

        ok, reason = validate_sentence_batch_uids(
            expected_uids=uids_batch,
            actual_batch=o,
            check_missing=True,
        )

        if not ok:
            raise Exception(reason)

        ok, reason = validate_batch_sentence(
            batch=o,
            max_len=999,
            prompt_max_len=999,
        )

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
        src_language=source_language,
        language=language,
        items_to_fix=items_to_fix_txt,
    )

    result: SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    logs = None
    print(f"[attemps={attemps}, id={batch_id}] After Translation Repair")
    logs = f"--------- [attemps={attemps}, id={batch_id}] After Translation Repair ---------------\n"
    logs += _build_items_to_fix(src_batch, trans_batch, issue_batch, previous_trans_batch, result)

    # Filter:
    # Exclude repaired translations that remain unchanged. (Means removing them from the recheck pool)
    prev_trans_map = { item.uid: item.val for item in trans_batch.items }
    result.items = [
        new_trans
        for new_trans in result.items
        if prev_trans_map[new_trans.uid] != new_trans.val # preseve the updated ones only
    ]

    return {
        "corrected_batches": { batch_id: result } if result.items else {},
        "pending_logs": [logs] if logs else [],
    }