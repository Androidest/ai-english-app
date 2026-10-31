from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.nodes._common import (
    MAX_TRANSLATION_RETRIES,
    map_by_id,
    validate_ids,
    validate_translation_text,
)
from app.workflow.schemas.translation import TranslationBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a professional translation editor.

Repair only the supplied failed translations.

Hard requirements:
- Preserve every record_id exactly.
- Return exactly one translation for every supplied record_id.
- Use the English source as the only semantic source of truth.
- Correct semantic inaccuracies.
- Preserve negation, tense/aspect, modality, numbers, quantities, dates,
  times, names, entities, and other important details.
- Do not add information that is not present in English.
- Do not remove information that is present in English.
- Produce natural target-language wording.
- Return only structured output.

For Chinese:
- Use natural Simplified Chinese.

For Indonesian:
- Use standard Bahasa Indonesia.
- Do not use Malaysian Malay.

Target language: Simplified Chinese.

Repair these Simplified Chinese translations.

Items:
{items}

Return exactly one repaired translation for every record_id.
"""


def repair_chinese(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Repair the Chinese translations that failed validation."""
    failed_ids = state["chinese_failed_ids"]

    if not failed_ids:
        return LessonGeneratorState()

    retry_count = state.get(
        "chinese_retry_count",
        0,
    )

    if retry_count >= MAX_TRANSLATION_RETRIES:
        raise RuntimeError(
            "Maximum Chinese translation retries exceeded for: "
            f"{failed_ids}"
        )

    english_map = map_by_id(
        state["english_items"]
    )

    chinese_map = map_by_id(
        state["chinese_items"]
    )

    items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
            "previous_translation": (
                chinese_map[record_id].text
                if record_id in chinese_map
                else ""
            ),
        }
        for record_id in failed_ids
    ]

    def verify_cb(o: TranslationBatch):
        ok, reason = validate_ids(
            expected_ids=failed_ids,
            actual_ids=[
                item.record_id
                for item in o.items
            ],
        )

        if not ok:
            raise Exception(
                f"Chinese repair alignment failure: {reason}"
            )

        text_failures = validate_translation_text(o.items)

        if text_failures:
            raise Exception(
                "Chinese translation repair failed basic validation: "
                f"{text_failures}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.4,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=TranslationBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        items=items,
    )

    result = llm.invoke(
        input=sys_prompt,
    )

    repair_map = map_by_id(result.items)

    merged = [
        repair_map.get(
            item.record_id,
            item,
        )
        for item in state["chinese_items"]
    ]

    return LessonGeneratorState(
        chinese_items=merged,
        chinese_failed_ids=[],
        chinese_retry_count=retry_count + 1,
    )
