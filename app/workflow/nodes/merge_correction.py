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

    updated_batches = {}
    remaining_recheck_ids = []
    for batch_id, batch in batches.items():
        if batch_id in pending_results_batches:
            # If this batch needs to be updated
            updated_batches[batch_id] = pending_results_batches[batch_id] 
            remaining_recheck_ids.append(batch_id)
        else:
            # remains the same
            updated_batches[batch_id] = batch

    remaining_attempts -= 1

    return { 
        f"{req.target_batches_key}": updated_batches,
        "processing_batch_ids": remaining_recheck_ids,
        "remaining_attempts": remaining_attempts,
        "issue_batches": Overwrite({}),
        "corrected_batches": Overwrite({}),
        "pending_logs": Overwrite([]),
        "logs": state["logs"] + state["pending_logs"]
    }
