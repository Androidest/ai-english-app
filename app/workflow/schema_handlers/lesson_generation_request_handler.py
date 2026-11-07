from app.workflow.states.lesson_generator_state import LessonGenerationRequest
from app.utils.types import CEFRLevel, Language


def validate_request(
    request: LessonGenerationRequest
) -> tuple[bool, str]:
    
    """Node: Validate the request"""

    errors = []

    if request.source_language not in Language.__args__:
        errors.append(f"- source_language must be one of these: {Language.__args__}, but '{request.source_language}' is given.")

    for l in request.translation_languages:
        if l not in Language.__args__:
            errors.append(f"- Translation languages must be one of these: {Language.__args__}, but '{l}' is given.")

    if request.source_max_len <= 0:
        errors.append("- source_max_len must be greater than 0.")

    if request.topic == "" or request.topic is None:
        errors.append("- topic must not be empty.")

    if request.difficulty not in CEFRLevel.__args__:
        errors.append(f"- difficulty must be one of these CEFR levels: {CEFRLevel.__args__}")

    if request.target_count <= 0:
        errors.append("- target_count must be greater than 0.")

    if request.batch_size <= 0:
        errors.append("- batch_size must be greater than 0.")

    if request.max_concurrency <= 0:
        errors.append("- max_concurrency must be greater than 0.")

    if errors:
        errors = ["[LessonGenerationRequest] the request contains invalid values:"] + errors
        return False, "\n".join(errors)

    return True, ""