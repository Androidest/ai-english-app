from langgraph.graph import END, START, StateGraph
import warnings

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.llm_config import LLMConfig
from app.workflow._core_.workflow_base import WorkflowBase
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.nodes.initialize_correction_request import initialize_correction_request
from app.workflow.nodes.empty_node import empty_node
from app.workflow.nodes.check_grammar_batch import fanout_check_grammar_batch, check_grammar_batch
from app.workflow.nodes.fix_grammar_batch import fanout_fix_grammar_batch, fix_grammar_batch
from app.workflow.nodes.merge_correction import merge_correction

RECURSION_LIMIT = 200

def warn_insufficient_attempts(state: LessonGeneratorState, info:str):
    if len(state["processing_batch_ids"]) > 0 and state["remaining_attempts"] == 0:
        warnings.warn(f"[Insufficient Attepmts] {info}")

class GrammarCorrector_Subgraph(WorkflowBase):
    """A subgraph/sub-workflow that checks and repairs the supplied batches"""

    def __init__(self, name:str):
        self.name = name
        super().__init__()

    def _build_graph(self):
        builder = StateGraph(
            state_schema=LessonGeneratorState,
            context_schema=BasicWorkflowContext,
        )

        INIT_REQUEST = f"[{self.name}] init_correction_request"
        START_NEXT_CORRECTION = f"[{self.name}] start_next_correction"
        CHECK_GRAMMAR_BATCH = f"[{self.name}] check_grammar_batch"
        FIX_GRAMMAR_BATCH = f"[{self.name}] fix_grammar_batch"
        MERGE_CORRECTION = f"[{self.name}] merge_correction"

        # -------------------- nodes -----------------------

        builder.add_node(INIT_REQUEST, initialize_correction_request)
        builder.add_node(START_NEXT_CORRECTION, empty_node)
        builder.add_node(CHECK_GRAMMAR_BATCH, check_grammar_batch)
        builder.add_node(FIX_GRAMMAR_BATCH, fix_grammar_batch)
        builder.add_node(MERGE_CORRECTION, merge_correction)

        # -------------------- edges -----------------------

        # Start
        builder.add_edge(START, INIT_REQUEST)
        builder.add_edge(INIT_REQUEST, START_NEXT_CORRECTION) 

        # Check
        def check_or_end(state: LessonGeneratorState):
            if len(state["processing_batch_ids"]) > 0 and state["remaining_attempts"] > 0:
                return fanout_check_grammar_batch(CHECK_GRAMMAR_BATCH, state)
            else:
                warn_insufficient_attempts(state, f"GrammarCorrector_Subgraph(name={self.name})")
                return END
        builder.add_conditional_edges(
            START_NEXT_CORRECTION,
            check_or_end,
            [CHECK_GRAMMAR_BATCH, END],
        )

        # Fix
        def fix_or_end(state: LessonGeneratorState):
            if len(state["processing_batch_ids"]) > 0:
                return fanout_fix_grammar_batch(FIX_GRAMMAR_BATCH, state)
            else:
                return END
        builder.add_conditional_edges(
            CHECK_GRAMMAR_BATCH,
            fix_or_end,
            [FIX_GRAMMAR_BATCH, END],
        )

        # Merge
        builder.add_edge(FIX_GRAMMAR_BATCH, MERGE_CORRECTION)
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
