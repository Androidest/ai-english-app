from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext


def make_apply_pending_batches_node(
    target_state_key: str,
) -> callable:

    """
    Create a 'apply_pending_batches' node according to the given target_state_key
    """
    
    def apply_pending_batches(
        state: LessonGeneratorState,
        runtime: Runtime[BasicWorkflowContext],
    ) -> LessonGeneratorState:
        
        """
        Node: Apply the pending batches to the target and clear the pending batches.
        """

        return { 
            f"{target_state_key}": copy.deepcopy(state["pending_batches"]),
            "pending_batches": Overwrite([]),
        }

    return apply_pending_batches