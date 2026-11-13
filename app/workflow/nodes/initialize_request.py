import uuid
from langgraph.types import Overwrite

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.schema_handlers.lesson_generation_request_handler import validate_request

def create_uid(index: int) -> str:
    """
    Create the application-generated immutable key for every sentence.
    The LLM is never asked to create these ids.
    """
    return f"uid_{index:03d}{uuid.uuid4().hex[:5]}" 

def initialize_request(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Validate the request and create the immutable record ids."""
    
    request = state["request"]

    ok, reason = validate_request(request)
    if not ok:
        raise ValueError(reason)

    target_ids = [
        create_uid(i + 1)
        for i in range(request.target_count)
    ]

    return LessonGeneratorState(
        target_ids=target_ids,
        previous_sentences=[],
        src_batches={},
        translations_dict={},
        pending_batches=Overwrite({}),
        logs=[],
    )
