from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow.schema_handlers.sentence_batch_handler import (
    merge_batch,
)
    
def merge_correction(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Update the pending results to the processing batches and clear all the temporary batches.
    """

    req = state["issue_correction_request"]
    batches = state[req.target_batches_key]
    corrected_batches = state["corrected_batches"]
    remaining_attempts = state["remaining_attempts"]

    updated_batches = {}
    for batch_id, old_batch in batches.items():
        if batch_id in corrected_batches:
            # If this batch needs to be updated
            updated_batches[batch_id] = merge_batch(
                base=old_batch, # original full batch
                updates=corrected_batches[batch_id], # partial updates
            )
        else:
            # remains the same
            updated_batches[batch_id] = old_batch

    remaining_attempts -= 1

    return { 
        f"{req.target_batches_key}": updated_batches,
        "processing_batches": corrected_batches.copy(), # re-check the corrected sentences in the next loop
        "remaining_attempts": remaining_attempts,
        "issue_batches": Overwrite({}),
        "corrected_batches": Overwrite({}),
        "pending_logs": Overwrite([]),
        "logs": state["logs"] + state["pending_logs"]
    }
