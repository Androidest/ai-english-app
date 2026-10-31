from app.workflow.nodes._common import validate_ids, validate_translation_text
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.valid_status import ValidStatus


def validate_indonesian(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Validate the Indonesian translation branch."""
    expected_ids = state["target_ids"]

    actual_ids = [
        item.record_id
        for item in state["indonesian_items"]
    ]

    failures: dict[str, str] = {}

    ok, reason = validate_ids(
        expected_ids=expected_ids,
        actual_ids=actual_ids,
    )

    if not ok:
        for record_id in expected_ids:
            failures[record_id] = reason

    failures.update(
        validate_translation_text(
            state["indonesian_items"]
        )
    )

    indonesian_failed_ids = sorted(failures.keys())

    return LessonGeneratorState(
        indonesian_failed_ids=indonesian_failed_ids,
        id_valid_status=(
            ValidStatus.SUCCESS
            if len(indonesian_failed_ids) == 0
            else ValidStatus.FAIL
        ),
        errors=[
            f"Indonesian validation: "
            f"{record_id}: {reason}"
            for record_id, reason
            in failures.items()
        ],
    )
