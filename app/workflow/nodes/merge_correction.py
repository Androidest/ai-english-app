from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext

    
def merge_correction(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Update the pending results to the processing batches and clear all the temporary batches.
    """

    req = state["issue_correction_request"]
    batches = state[req.target_batches_key]
    pending_results_batches = state["corrected_batches"]
    remaining_attempts = state["remaining_attempts"]

    batches = {
        batch_id: 
            pending_results_batches[batch_id] # updates
            if batch_id in pending_results_batches else # If this batch needs to be updated
            batch # remains the same
        
        for batch_id, batch in batches.items()
    }

    remaining_recheck_ids = [ batch_id for batch_id in pending_results_batches.keys() ]
    
    return LessonGeneratorState( 
        **{ f"{req.target_batches_key}": batches },
        processing_batch_ids=remaining_recheck_ids,
        remaining_attempts=remaining_attempts-1,
        issue_batches=Overwrite({}),
        corrected_batches=Overwrite({}),
    )
