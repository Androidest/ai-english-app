from langgraph.runtime import Runtime
from langgraph.types import Send
import warnings
import json

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
    merge_batch,
)

SYS_PROMPT_TEMPLATE = """You are an expert grammar and translation corrector.
Each supplied entry includes a source-translation pair and a repair reason describing the grammar and translation (alignment) issues in the translated sentence.
Repair only the translated sentences listed below according to their respective repair reasons.

Hard requirements:
- Generate exactly one repaired translated sentence per UID.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured repaired data. Do not add extra explanations, commentary, or preamble.
- Fix only the grammar and translation issue described in the repair reason for each translated sentence. Do not make unrelated changes.
- Do not directly copy the supplied sentences. Modification is required for all the translated sentences; 
- Do not repair or output the source sentences. Only the translation is modified.
- Do not omit meaningful information from the source.
- Do not add information that does not exist in the source.

Source Language:
{src_language}

Translation language:
{language}

Translated sentences to repair (with repair reasons and source sentences):
{items_to_fix}

Now, Output the updated (repaired) translations.
"""


COPY_ERROR_TEMPLATE = """The following uids were returned with text identical to the original translation:
{uids}

You should fix the issues for these uids according to their reasons.
These translation should be modified, not copied.
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
    src_batch: SentenceBatch, 
    trans_batch: SentenceBatch,
    issue_batch: IssueBatch,
    output_batch: SentenceBatch = None, # for testing
) -> str:

    """
    Build the repair payload: 
    Each line contains one source-translation sentence pair 
    followed by an UID and a repair reason.
    """

    uid_src_map = { item.uid: item.val for item in src_batch.items }
    uid_tran_map = { item.uid: item.val for item in trans_batch.items }
    if output_batch:
        uid_out_map = { item.uid: item.val for item in output_batch.items }

    items = []
    for item in issue_batch.issues:
        obj = {
            "uid": item.uid,
            "source": normalize_text(uid_src_map[item.uid]),
            "translation": normalize_text(uid_tran_map[item.uid]),
            "reason": item.reason,
        }
        if output_batch:
            obj["repaired"] = normalize_text(uid_out_map[item.uid])

        items.append(json.dumps(
            obj, 
            indent=0, 
            ensure_ascii=False
        ))

    text = "\n".join(items)
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

    src_batch = main_state["src_batches"][batch_id]
    trans_batch = state["batch"]
    issue_batch = main_state["issue_batches"][batch_id]

    source_language = req.source_language
    language = req.language
    
    if len(issue_batch.issues) == 0:
        return LessonGeneratorState(corrected_batches={})

    uids_batch = set(issue.uid for issue in issue_batch.issues)
    items_to_fix_txt = _build_items_to_fix(src_batch, trans_batch, issue_batch)

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
        for item in trans_batch.items:
            if item.uid in sent_by_id and sent_by_id[item.uid] == item.val:
                error_uids.append(f'- uid="{item.uid}"')

        if error_uids:
            warnings.warn(f"[fix_translation_batch] Repeating sentences: {[ item.uid for item in o.items ]}")
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
        src_language=source_language,
        language=language,
        items_to_fix=items_to_fix_txt,
    )

    result: SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    if result.items:
        print("------------ After Repair ---------------")
        print(_build_items_to_fix(src_batch, trans_batch, issue_batch, result))

    merged_batch = merge_batch(
        base=trans_batch,
        updates=result,
    )

    return LessonGeneratorState(
        corrected_batches={ batch_id: merged_batch },
    )