from app.workflow.nodes._common import validate_ids, validate_translation_text
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.valid_status import ValidStatus


def validate_chinese(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Validate the Chinese translation branch."""
    expected_ids = state["target_ids"]

    actual_ids = [
        item.record_id
        for item in state["chinese_items"]
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
            state["chinese_items"]
        )
    )

    chinese_failed_ids = sorted(failures.keys())

    return LessonGeneratorState(
        chinese_failed_ids=chinese_failed_ids,
        cn_valid_status=(
            ValidStatus.SUCCESS
            if len(chinese_failed_ids) == 0
            else ValidStatus.FAIL
        ),
        errors=[
            f"Chinese validation: "
            f"{record_id}: {reason}"
            for record_id, reason
            in failures.items()
        ],
    )
