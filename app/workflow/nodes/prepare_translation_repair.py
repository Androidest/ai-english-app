from langgraph.runtime import Runtime

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.schemas.issue_correction_request import IssueCorrectionRequest
from app.workflow._core_.context import BasicWorkflowContext

    
def prepare_translation_repair(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Prepare the request for the Translation Correction subgraph.
    """

    req = state["request"]
    source_language = req.source_language
    cur_lang_idx = len(state["translations_dict"])
    cur_language = req.translation_languages[cur_lang_idx]

    request = IssueCorrectionRequest(
        source_language=source_language,
        language=cur_language,
        target_batches_key="translated_batches",
        max_attempts=2,
    )

    return LessonGeneratorState(
        issue_correction_request=request
    )
