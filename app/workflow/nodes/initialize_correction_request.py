from langgraph.runtime import Runtime
from langgraph.types import Overwrite

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext

    
def initialize_correction_request(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Initialize the issue correction request
    """

    req = state["issue_correction_request"]
    batches = state[req.target_batches_key]

    return LessonGeneratorState(
        processing_batch_ids=[ batch_id for batch_id in batches.keys() ],
        remaining_attempts=req.max_attempts,
        issue_batches=Overwrite({}),
        corrected_batches=Overwrite({}),
        pending_logs=Overwrite([]),
    )
