from langgraph.runtime import Runtime

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow.schema_handlers.diversity_plan_handler import batchify_plan 
from app.workflow.states.lesson_generator_state import LessonGeneratorState


def batchify_plan_and_ids(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Batchify plan and unique IDs according to the given batch size
    """

    request = state["request"]
    diversity_plan = state["diversity_plan"]
    target_ids = state["target_ids"]

    return {

        "target_ids_batches": [
            set(target_ids[i : i+request.batch_size])
            for i in range(0, len(target_ids), request.batch_size)
        ],
        
        "diversity_plan_batches": batchify_plan(
            diversity_plan=diversity_plan, 
            batch_size=request.batch_size,
        ),
    }
