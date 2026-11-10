from langgraph.graph import END, START, StateGraph
import warnings

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.llm_config import LLMConfig
from app.workflow._core_.workflow_base import WorkflowBase
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.nodes.initialize_correction_request import initialize_correction_request
from app.workflow.nodes.empty_node import empty_node
from app.workflow.nodes.check_translation_batch import fanout_check_translation_batch, check_translation_batch
from app.workflow.nodes.fix_translation_batch import fanout_fix_translation_batch, fix_translation_batch
from app.workflow.nodes.merge_correction import merge_correction

RECURSION_LIMIT = 200

def warn_insufficient_attempts(state: LessonGeneratorState):
    if len(state["processing_batch_ids"]) > 0 and state["remaining_attempts"] == 0:
        warnings.warn(f"[Insufficient Attepmts] TranslationCorrection_Subgraph")

class TranslationCorrection_Subgraph(WorkflowBase):
    """A subgraph/sub-workflow that checks and repairs the translation of the supplied batches"""

    def _build_graph(self):
        builder = StateGraph(
            state_schema=LessonGeneratorState,
            context_schema=BasicWorkflowContext,
        )

        INIT_REQUEST = "init_correction_request"
        START_NEXT_CORRECTION = "start_next_correction"
        CHECK_TRANSLATION_BATCH = "check_translation_batch"
        FIX_TRANSLATION_BATCH = "fix_translation_batch"
        MERGE_CORRECTION = "merge_correction"

        # -------------------- nodes -----------------------

        builder.add_node(INIT_REQUEST, initialize_correction_request)
        builder.add_node(START_NEXT_CORRECTION, empty_node)
        builder.add_node(CHECK_TRANSLATION_BATCH, check_translation_batch)
        builder.add_node(FIX_TRANSLATION_BATCH, fix_translation_batch)
        builder.add_node(MERGE_CORRECTION, merge_correction)

        # -------------------- edges -----------------------

        # Start
        builder.add_edge(START, INIT_REQUEST)
        builder.add_edge(INIT_REQUEST, START_NEXT_CORRECTION) 

        # Check
        def check_or_end(state: LessonGeneratorState):
            if len(state["processing_batch_ids"]) > 0 and state["remaining_attempts"] > 0:
                return fanout_check_translation_batch(CHECK_TRANSLATION_BATCH, state)
            else:
                warn_insufficient_attempts(state)
                return END
        builder.add_conditional_edges(
            START_NEXT_CORRECTION,
            check_or_end,
            [CHECK_TRANSLATION_BATCH, END],
        )

        # Fix
        def fix_or_end(state: LessonGeneratorState):
            if len(state["processing_batch_ids"]) > 0:
                return fanout_fix_translation_batch(FIX_TRANSLATION_BATCH, state)
            else:
                return END
        builder.add_conditional_edges(
            CHECK_TRANSLATION_BATCH,
            fix_or_end,
            [FIX_TRANSLATION_BATCH, END],
        )

        # Merge
        builder.add_edge(FIX_TRANSLATION_BATCH, MERGE_CORRECTION)
        # Loop
        builder.add_edge(MERGE_CORRECTION, START_NEXT_CORRECTION)

        return builder.compile()

    def invoke(
        self,
        input: LessonGenerationRequest,
        llm_config: LLMConfig,
        user_id: str,
    ) -> list[dict[str, str]]:

        pass


    async def ainvoke(
        self,
        input: LessonGenerationRequest,
        llm_config: LLMConfig,
        user_id: str,
    ) -> list[dict[str, str]]:

        pass
