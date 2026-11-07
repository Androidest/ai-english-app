from langgraph.graph import END, START, StateGraph

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.llm_config import LLMConfig
from app.workflow._core_.llm_runtime import LLMRuntime
from app.workflow._core_.workflow_base import WorkflowBase
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.nodes.initialize_request import initialize_request
from app.workflow.nodes.plan_diversity import plan_diversity
from app.workflow.nodes.batchify_plan_and_ids import batchify_plan_and_ids
from app.workflow.nodes.gen_src_batch import gen_src_batch
from app.workflow.nodes.fix_grammar_batch import fix_grammar_batch, fanout_fix_grammar_batch
from app.workflow.nodes.apply_pending_batches import make_apply_pending_batches_node
from app.workflow.nodes.empty_node import empty_node
from app.workflow.nodes.translate_src_batch import translate_src_batch, fanout_translation
from app.workflow.nodes.save_fixed_translation import save_fixed_translation
from app.workflow.nodes.final_merge_by_uid import final_merge_by_uid

RECURSION_LIMIT = 200

class LessonGenerator(WorkflowBase):
    """A workflow that generates multilingual lesson sentences."""


    def _build_graph(self):
        """Multilingual (EN/CN/ID) lesson generator workflow."""

        builder = StateGraph(
            state_schema=LessonGeneratorState,
            context_schema=BasicWorkflowContext,
        )

        # -------------------- nodes -----------------------

        # Source generation
        builder.add_node("initialize_request", initialize_request)
        builder.add_node("plan_diversity", plan_diversity)
        builder.add_node("batchify_plan_and_ids", batchify_plan_and_ids)
        builder.add_node("gen_src_batch", gen_src_batch)
        builder.add_node("fix_src_grammar_batch", fix_grammar_batch)
        builder.add_node("apply_pending_to_src", make_apply_pending_batches_node("src_batches"))

        # Translation
        builder.add_node("start_translation", empty_node)
        builder.add_node("translate_src_batch", translate_src_batch)
        builder.add_node("apply_pending_to_trans", make_apply_pending_batches_node("translated_batches"))
        builder.add_node("fix_trans_grammar_batch", fix_grammar_batch)
        builder.add_node("save_fixed_translation", save_fixed_translation)

        # final merge
        builder.add_node("final_merge_by_uid", final_merge_by_uid)

        # -------------------- edges -----------------------

        # Entry, Source generation
        builder.add_edge(START, "initialize_request")
        builder.add_edge("initialize_request", "plan_diversity")
        builder.add_edge("plan_diversity", "batchify_plan_and_ids")
        builder.add_edge("batchify_plan_and_ids", "gen_src_batch")

        # loop to source generation or go forward to fanned-out parallel grammar batch fixing. 
        def loop_or_fanout(state: LessonGeneratorState):
            if len(state["src_batches"]) < len(state["target_ids_batches"]):
                return "gen_src_batch" # loop: generate the next batch
            else:
                return fanout_fix_grammar_batch("fix_src_grammar_batch", state) 
            
        builder.add_conditional_edges(
            "gen_src_batch",
            loop_or_fanout,
            ['gen_src_batch', "fix_src_grammar_batch"],
        )
        builder.add_edge("fix_src_grammar_batch", "apply_pending_to_src")

        # Translation
        builder.add_edge("apply_pending_to_src", "start_translation")

        builder.add_conditional_edges(
            "start_translation",
            lambda state: fanout_translation("translate_src_batch", state),
            ["translate_src_batch"],
        )
        builder.add_edge("translate_src_batch", "apply_pending_to_trans")

        # Fix translation grammar
        builder.add_conditional_edges(
            "apply_pending_to_trans",
            lambda state: fanout_fix_grammar_batch("fix_trans_grammar_batch", state) ,
            ["fix_trans_grammar_batch"],
        )
        builder.add_edge("fix_trans_grammar_batch", "save_fixed_translation")

        # loop to the next translation or concatenate all the results.
        def loop_or_merge(state: LessonGeneratorState):
            if len(state["translations_dict"]) < len(state["request"].translation_languages):
                return "start_translation" # loop: translate the next batch
            else:
                return "final_merge_by_uid"
            
        builder.add_conditional_edges(
            "save_fixed_translation",
            loop_or_merge,
            ["start_translation", "final_merge_by_uid"],
        )

        # final step
        builder.add_edge("final_merge_by_uid", END)

        return builder.compile()


    def invoke(
        self,
        input: LessonGenerationRequest,
        llm_config: LLMConfig,
        user_id: str,
    ) -> list[dict[str, str]]:

        """
        Generate multilingual lesson sentences.
        args:
            input: The generation request.
            llm_config: The expected LLM that is supposed be used by the workflow.
            user_id: The id of the requesting user.
        """

        final_state: LessonGeneratorState = self.graph.invoke(
            input=LessonGeneratorState(
                request=input
            ),
            context=BasicWorkflowContext(
                user_id=user_id,
                llm_runtime=LLMRuntime(config=llm_config),
            ),
            config={
                "recursion_limit": RECURSION_LIMIT,
                "max_concurrency": input.max_concurrency,
            },
        )

        return final_state["final_items"]


    async def ainvoke(
        self,
        input: LessonGenerationRequest,
        llm_config: LLMConfig,
        user_id: str,
    ) -> list[dict[str, str]]:

        """Async version of `invoke`."""

        final_state: LessonGeneratorState = await self.graph.ainvoke(
            input=LessonGeneratorState(
                request=input
            ),
            context=BasicWorkflowContext(
                user_id=user_id,
                llm_runtime=LLMRuntime(config=llm_config),
            ),
            config={
                "recursion_limit": RECURSION_LIMIT,
                "max_concurrency": input.max_concurrency,
            },
        )

        return final_state["final_items"]
