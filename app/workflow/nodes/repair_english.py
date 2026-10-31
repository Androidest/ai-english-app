from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.nodes._common import (
    MAX_ENGLISH_RETRIES,
    map_by_id,
    validate_english_text,
    validate_ids,
)
from app.workflow.schemas.english_sentence import EnglishBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are an expert English-learning content editor.

Repair only the supplied failed English source records.

Hard requirements:
- Preserve every record_id exactly.
- Return exactly one repaired English sentence for every supplied record_id.
- Generate exactly one sentence per record.
- Keep the original semantic intent whenever possible.
- Fix grammar, unnatural wording, formatting, duplication, or other supplied
  validation problems.
- Do not duplicate another supplied sentence.
- Keep the result concise and appropriate for the requested difficulty.
- Return only structured output.

Topic:
{topic}

Difficulty:
{difficulty}

Repair these failed English records:

{failed_items}

Return exactly one repaired item for every record_id.
"""


def repair_english(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Repair the English records that failed validation."""
    failed_ids = state["english_failed_ids"]

    if not failed_ids:
        return LessonGeneratorState()

    retry_count = state.get(
        "english_retry_count",
        0,
    )

    if retry_count >= MAX_ENGLISH_RETRIES:
        raise RuntimeError(
            "Maximum English retry count exceeded for: "
            f"{failed_ids}"
        )

    current_map = map_by_id(
        state["english_items"]
    )

    failed_items = [
        {
            "record_id": record_id,
            "english": (
                current_map[record_id].english
                if record_id in current_map
                else ""
            ),
        }
        for record_id in failed_ids
    ]

    def verify_cb(o: EnglishBatch):
        ok, reason = validate_ids(
            expected_ids=failed_ids,
            actual_ids=[
                item.record_id
                for item in o.items
            ],
        )

        if not ok:
            raise Exception(
                f"English repair alignment failure: {reason}"
            )

        text_failures = validate_english_text(o.items)

        if text_failures:
            raise Exception(
                "English repair still failed basic validation: "
                f"{text_failures}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.8,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=EnglishBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        topic=state["topic"],
        difficulty=state["difficulty"],
        failed_items=failed_items,
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
        for item in state["english_items"]
    ]

    return LessonGeneratorState(
        english_items=merged,
        english_failed_ids=[],
        english_retry_count=retry_count + 1,
    )
