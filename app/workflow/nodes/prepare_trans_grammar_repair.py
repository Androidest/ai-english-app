from langgraph.runtime import Runtime

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.schemas.issue_correction_request import IssueCorrectionRequest
from app.workflow._core_.context import BasicWorkflowContext

    
def prepare_trans_grammar_repair(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Prepare the request for the source-grammar-repairing subgraph.
    """

    translation_languages = state["request"].translation_languages
    cur_lang_idx = len(state["translations_dict"])
    cur_language = translation_languages[cur_lang_idx]

    request = IssueCorrectionRequest(
        language=cur_language,
        target_batches_key="translated_batches",
        max_attempts=2,
    )

    return LessonGeneratorState(
        issue_correction_request=request
    )
