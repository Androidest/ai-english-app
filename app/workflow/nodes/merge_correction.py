from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.schemas.sentence_batch import SentenceBatch
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
    batches: dict[str, SentenceBatch] = state[req.target_batches_key]
    corrected_batches = state["corrected_batches"]
    remaining_attempts = state["remaining_attempts"]

    pre_corrected_batches: dict[str, dict[str, str]] = {}
    updated_batches = {}
    
    for batch_id, old_batch in batches.items():

        # If this batch needs to be updated
        if batch_id in corrected_batches:
            # corrected_batches: items after the correction (output)
            changes_batch = corrected_batches[batch_id]

            # update the target batches
            updated_batches[batch_id] = merge_batch(
                base=old_batch, # original full batch
                updates=changes_batch, # partial updates
            )

            # build the pre_corrected_batches: items before the correction (input)
            corrected_uid = set([
                item.uid for item in changes_batch.items
            ])
            pre_corrected_batches[batch_id] = {
                item.uid: item.val
                for item in old_batch.items
                if item.uid in corrected_uid
            }

        # remains the same
        else:
            updated_batches[batch_id] = old_batch

    remaining_attempts -= 1

    return { 
        f"{req.target_batches_key}": updated_batches,
        "processing_batches": corrected_batches.copy(), # re-check the corrected sentences in the next loop
        "remaining_attempts": remaining_attempts,
        "issue_batches": Overwrite({}),
        "corrected_batches": Overwrite({}),
        "pre_corrected_batches": pre_corrected_batches,

        "pending_logs": Overwrite([]),
        "logs": state["logs"] + state["pending_logs"]
    }
