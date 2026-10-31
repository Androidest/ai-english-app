from app.workflow.nodes._common import map_by_id
from app.workflow.states.lesson_generator_state import LessonGeneratorState


def merge_by_id(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Join the three language branches by the immutable record id.

    No LLM is involved. Final public keys are EN, CN and ID.
    """
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

    if set(english_map) != set(target_ids):
        raise ValueError(
            "English IDs do not exactly match target IDs."
        )

    if set(chinese_map) != set(target_ids):
        raise ValueError(
            "Chinese IDs do not exactly match target IDs."
        )

    if set(indonesian_map) != set(target_ids):
        raise ValueError(
            "Indonesian IDs do not exactly match target IDs."
        )

    final_items = [
        {
            "EN": english_map[record_id].english,
            "CN": chinese_map[record_id].text,
            "ID": indonesian_map[record_id].text,
        }
        for record_id in target_ids
    ]

    return LessonGeneratorState(
        final_items=final_items,
    )
