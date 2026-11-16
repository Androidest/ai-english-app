from langgraph.runtime import Runtime
from langgraph.types import Send
from langgraph.config import get_stream_writer

from app.workflow.schema_handlers.commons import item_to_text
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.stream_data import StreamData
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

SYS_PROMPT_TEMPLATE = """You are a translation quality gate, not a style editor.
Report only substantive translation or grammar defects. Do NOT repair them.

Hard requirements:
- Report an issue only when substantive defects are identified. Classify each one honestly.
- Each issue must include uid, reason, severity and confidence.
- Treat UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- reason:
    1. Must be a single line;
    2. Must be written in the target translation language;
    3. Describe the defect only. Do not suggest replacement wording;
    4. State the defect precisely;
- severity must be one of the following: 
    1. "critical" = reversed/omitted/added substantive information, wrong number/date/name, or broken grammar causing misunderstanding;
    2. "major" = substantive alignment or grammar defect but still understandable;
    3. "minor" = style/wording preference only;
- confidence must be one of the following: 
    1. "high" = the defect is verifiable from explicit textual evidence, e.g. wrong number/date/name, reversed negation, clear omission/addition of substantive info, hard grammatical error, or an unambiguous mistranslation; 
    2. "low" = the judgment depends on context inference, cultural/idiomatic knowledge, source ambiguity, borderline register, or a plausible alternative reading.
- Output only structured issue data. Do not add extra explanations, commentary, or preamble.
- Only output issues with severity "critical", "major" or "minor". Omit entries with zero defects.
- Return `issues` as an EMPTY list if there is no issue.
- Source errors are the baseline. Do not flag a faithful rendering of a source error as a translation or grammar issue of the target text.
- [Top priority] Check substantive alignment on:
    1. Semantic intent
    2. Original meaning
    3. Negation
    4. Tense/aspect meaning
    5. Modality
    6. Numbers and quantities
    7. Dates and times
    8. Names and named entities
    9. Causal relationship
    10. Omission/addition information
- Check the following only when it causes misleading register mismatch:
    1. Tone
    2. Wording style
- For culture-specific items (food, dishes, places, institutions, festivals, measures, titles, brands), flag when: 
    1. the translation uses a non-established literal calque where the target language has a commonly accepted rendering; 
    2. the item is left in the source language though the target language has an established term; 
    3. a transliteration is used where an established rendering exists, or an established rendering is replaced by an obscure literal one. Do not flag when the chosen rendering is a recognized common usage in the target language, even if another valid variant exists. This applies to all language pairs.


Source Language:
{src_language}

Translation language:
{language}

Inspect the following {src_language}-{language} pairs:
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
    return [
        Send(
            node=node,
            arg=ParallelBatchState(
                batch_id=id,
                batch=batch,
                main_state=state,
            )  # local state
        )
        for id, batch in state['processing_batches'].items()
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

    # Filter:
    # Preserve only issues with high confidence, and severity of "critical" or "major".
    result.issues = [
        issue
        for issue in result.issues
        if issue.confidence == "high" and issue.severity in ("critical", "major") 
    ]

    if result.issues:
        return {
            "issue_batches": { batch_id: result },
        }
    
    else:
        writer = get_stream_writer()
        writer(StreamData(
            type=f"pass_trans_{language}",
            processed_count=len(src_batch.items),
        ))
        
        return {}