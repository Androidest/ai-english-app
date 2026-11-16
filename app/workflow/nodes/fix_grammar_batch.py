from langgraph.runtime import Runtime
from app.workflow.schema_handlers.commons import item_to_text
from langgraph.types import Send
import warnings

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

SYS_PROMPT_TEMPLATE = """You are a native-speaker grammar and fluency editor.
Each entry includes a UID, the current sentence, a repair reason describing a grammar or naturalness defect in that sentence, and optional previous_val.
Repair only the defects described by the reason.

Input fields per entry:
- uid: the key.
- val: the current version of the sentence.
- reason: the grammar/naturalness defect reported for `val`.
- previous_val (optional): the value of `val` BEFORE the previous repair round. Absent on the first round.

How to use previous_val:
- If previous_val is absent: treat `val` as the original sentence and repair normally.
- If `reason` describes a DIFFERENT defect not addressed by the previous change, repair it.
- If `reason` is a synonym/style/elegance preference, or asks to revert/contradict the direction of the previous sentence (oscillation, e.g. "use A" then "use B" then "use A"), return `val` UNCHANGED as the current repaired sentence for that UID.
- If `reason` restates the SAME defect that previous_val already attempted to fix and the current text is a reasonable faithful rendering, return `val` UNCHANGED as the current repaired sentence for that UID.

Hard requirements:
- Generate exactly one repaired sentence per UID.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured repaired data. Do not add extra explanations, commentary, or preamble.
- Fix only the defect described in the repair reason. Do not make unrelated changes.
- Preserve all of the following whenever possible from the original sentence:
    1. Tone
    2. Vocabulary difficulty level
    3. Sentence length (Fixing defects takes higher priority than this)
    4. Semantic intent
    5. Numbers and quantities
    6. Dates and times
    7. Names and named entities 

Target language:
{language}

Sentences to repair (with repair reasons):
{items_to_fix}

Now, Output the updated sentences.
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


def _build_issue_text(
    batch: SentenceBatch, 
    issue_batch: IssueBatch,
    previous_batch: dict[str, str],
    output_batch: SentenceBatch = None,
) -> str:

    """
    Build the repair payload: only sentences with reported issues, each with its reason.
    """

    uid_issue_map = {issue.uid: issue.reason for issue in issue_batch.issues}
    if output_batch:
        uid_out_map = {item.uid: item.val for item in output_batch.items}

    items = []
    for item in batch.items:
        if item.uid in uid_issue_map:
            new_item = {
                "uid": item.uid,
                "val": normalize_text(item.val),
                "reason": normalize_text(uid_issue_map[item.uid]),
            }

            if previous_batch:
                new_item["previous_val"] = normalize_text(previous_batch[item.uid]),

            if output_batch:
                new_item["repaired"] = normalize_text(uid_out_map[item.uid])
            items.append(new_item)
                        
    text = item_to_text(items)
    return text


def fix_grammar_batch(
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
    
    batch = state["batch"]
    issue_batch = main_state["issue_batches"][batch_id]
    language = main_state["issue_correction_request"].language
    pre_corrected_batches = main_state["pre_corrected_batches"]
    previous_batch = None

    if len(pre_corrected_batches) > 0:
        previous_batch = pre_corrected_batches[batch_id]
        
    if len(issue_batch.issues) == 0:
        return {
            "corrected_batches":{}
        }

    uids_batch = set(issue.uid for issue in issue_batch.issues)
    items_to_fix_txt = _build_issue_text(batch, issue_batch, previous_batch)

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
        language=language,
        items_to_fix=items_to_fix_txt,
    )

    result: SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    logs = None
    print(f"[attemps={attemps}, id={batch_id}] After Grammar Repair")
    logs = f"--------- [attemps={attemps}, id={batch_id}] After Grammar Repair ---------------\n"
    logs += _build_issue_text(batch, issue_batch, previous_batch, result)

    # Filter:
    # Exclude repaired sentences that remain unchanged. (Means removing them from the recheck pool)
    prev_item_map = { item.uid: item.val for item in batch.items }
    result.items = [
        new_item
        for new_item in result.items
        if prev_item_map[new_item.uid] != new_item.val # preseve the updated ones only
    ]

    return {
        "corrected_batches": { batch_id: result } if result.items else {},
        "pending_logs": [logs] if logs else [],
    }