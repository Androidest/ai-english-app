from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.nodes._common import map_by_id, validate_ids
from app.workflow.schemas.translation_qa import TranslationQABatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a strict multilingual translation quality evaluator.

Evaluate every supplied record independently.

For each record, determine:
1. Whether the Chinese translation accurately conveys the English meaning.
2. Whether the Indonesian translation accurately conveys the English meaning.
3. Whether negation is preserved.
4. Whether tense/aspect meaning is preserved.
5. Whether modality is preserved.
6. Whether numbers and quantities are preserved.
7. Whether dates and times are preserved.
8. Whether names and entities are preserved.
9. Whether important information is missing.
10. Whether unsupported information has been added.
11. Whether the translation is sufficiently natural for a language-learning
    application.

Different grammatical structures are acceptable. Do not require literal
word-for-word translation.

Do not rewrite translations.
Only return structured QA results.

Evaluate every multilingual record below.

Records:
{qa_items}

Return exactly one QA result for every record_id.
"""


def semantic_alignment_qa(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Semantically evaluate the merged multilingual dataset."""
    target_ids = state["target_ids"]

    english_map = map_by_id(
        state["english_items"]
    )
    chinese_map = map_by_id(
        state["chinese_items"]
    )
    indonesian_map = map_by_id(
        state["indonesian_items"]
    )

    qa_items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
            "chinese": chinese_map[record_id].text,
            "indonesian": indonesian_map[record_id].text,
        }
        for record_id in target_ids
    ]

    def verify_cb(o: TranslationQABatch):
        ok, reason = validate_ids(
            expected_ids=target_ids,
            actual_ids=[
                item.record_id
                for item in o.items
            ],
        )

        if not ok:
            raise Exception(
                f"Semantic QA alignment failure: {reason}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.1,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=TranslationQABatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        qa_items=qa_items,
    )

    result = llm.invoke(
        input=sys_prompt,
    )

    chinese_failed = [
        item.record_id
        for item in result.items
        if not item.chinese_ok
    ]

    indonesian_failed = [
        item.record_id
        for item in result.items
        if not item.indonesian_ok
    ]

    qa_errors = [
        f"{item.record_id}: {item.reason}"
        for item in result.items
        if not item.chinese_ok
        or not item.indonesian_ok
    ]

    return LessonGeneratorState(
        chinese_failed_ids=chinese_failed,
        indonesian_failed_ids=indonesian_failed,
        errors=qa_errors,
    )
