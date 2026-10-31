from app.workflow.nodes._common import DEFAULT_BATCH_SIZE, create_record_id
from app.workflow.states.lesson_generator_state import LessonGeneratorState


def initialize_request(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Validate the request and create the immutable record ids."""
    target_count = state["target_count"]

    if target_count <= 0:
        raise ValueError("target_count must be greater than 0.")

    batch_size = state.get("batch_size", DEFAULT_BATCH_SIZE)

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")

    target_ids = [
        create_record_id(i + 1)
        for i in range(target_count)
    ]

    return LessonGeneratorState(
        target_ids=target_ids,
        batch_size=batch_size,
        english_items=[],
        chinese_items=[],
        indonesian_items=[],
        current_english_batch_ids=[],
        english_failed_ids=[],
        chinese_failed_ids=[],
        indonesian_failed_ids=[],
        english_retry_count=0,
        chinese_retry_count=0,
        indonesian_retry_count=0,
        final_items=[],
        errors=[],
    )
