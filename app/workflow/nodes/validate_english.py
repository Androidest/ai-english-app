from app.workflow.nodes._common import validate_english_text, validate_ids
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.valid_status import ValidStatus


def validate_english(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Validate the current English batch and decide the next step."""
    current_ids = set(
        state.get(
            "current_english_batch_ids",
            [],
        )
    )

    batch = [
        item
        for item in state["english_items"]
        if item.record_id in current_ids
    ]

    expected_ids = state["current_english_batch_ids"]

    actual_ids = [item.record_id for item in batch]

    failures: dict[str, str] = {}

    ok, reason = validate_ids(
        expected_ids=expected_ids,
        actual_ids=actual_ids,
    )

    if not ok:
        for record_id in expected_ids:
            failures[record_id] = reason

    text_failures = validate_english_text(batch)

    failures.update(text_failures)

    english_failed_ids = sorted(failures.keys())

    valid_status = ValidStatus.SUCCESS

    if len(english_failed_ids) > 0:
        valid_status = ValidStatus.FAIL
    elif len(state["english_items"]) < state["target_count"]:
        valid_status = ValidStatus.PENDING_BATCH

    return LessonGeneratorState(
        english_failed_ids=english_failed_ids,
        valid_status=valid_status,
        errors=[
            f"English validation: {record_id}: {reason}"
            for record_id, reason
            in failures.items()
        ],
    )
