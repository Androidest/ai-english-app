from langgraph.runtime import Runtime

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.schemas.issue_correction_request import IssueCorrectionRequest
from app.workflow._core_.context import BasicWorkflowContext

    
def prepare_src_grammar_repair(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Prepare the request for the Grammar Correction subgraph.
    """

    request = IssueCorrectionRequest(
        language=state["request"].source_language,
        target_batches_key="src_batches",
        max_attempts=4,
    )

    return {
        "issue_correction_request": request
    }
