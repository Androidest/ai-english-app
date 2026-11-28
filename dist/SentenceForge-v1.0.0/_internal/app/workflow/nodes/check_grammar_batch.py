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
from app.workflow.schema_handlers.issue_batch_handler import (
    validate_issue_batch_uids,
    validate_batch_reasons,
)

SYS_PROMPT_TEMPLATE = """You are an expert content grammar checker.
Report only substantive grammar defects. Do NOT repair them.

Hard requirements:
- Report an issue only when substantive defects are identified. Classify each one honestly.
- Report only defects in: 
    1. grammar
    2. syntax
    3. word order
    4. agreement
    5. tense consistency
    6. articles/prepositions
    7. collocations
    8. punctuation
    9. phrasing that is unnatural or non-idiomatic to native speakers
    10. fluency
- Each issue must include uid, reason, severity and confidence.
- Treat UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- reason:
    1. Must be a single line;
    2. Must be written in the target language;
    3. Describe the defect only;
    4. State the defect precisely;
- severity must be one of the following: 
    1. "critical" = broken grammar, incorrect syntax, faulty word order, tense inconsistency, and articles/prepositions issues that cause misunderstanding;
    2. "major" = grammatical defect but still understandable, unnatural phrasing, non-idiomatic for native speakers, collocations errors, fluency issues, punctuation or capitalization issues;
    3. "minor" = style/wording preference only;
- confidence must be one of the following: 
    1. "high" = the defect is verifiable from explicit textual evidence; 
    2. "low" = the judgment depends on context inference, cultural/idiomatic knowledge, borderline register, or a plausible alternative reading.
- Output only structured issue data. Do not add extra explanations, commentary, or preamble.
- Omit entries where the sentence is grammatically correct (severity is none, no defects).
- Return `issues` as an EMPTY list if all sentences are grammatically correct.
- Do not return any repaired sentence text.
- The issues should consider preserving the following whenever possible from the original text:
    1. Tone
    2. Vocabulary difficulty level
    3. Semantic intent
    4. Wording style

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


def check_grammar_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """
    Node: Check the batch and report only problematic sentences with UID and reason.
    """

    main_state = state["main_state"]
    batch_id = state["batch_id"]
    batch = state["batch"]
    language = main_state["issue_correction_request"].language

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
            type=f"pass_grammar",
            processed_count=len(batch.items),
        ))

        return {}