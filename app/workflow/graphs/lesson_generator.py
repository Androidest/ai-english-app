from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.llm_config import LLMConfig
from app.workflow._commons_.llm_runtime import LLMRuntime
from app.workflow.nodes.final_validation import final_validation
from app.workflow.nodes.generate_english import generate_english
from app.workflow.nodes.initialize_request import initialize_request
from app.workflow.nodes.merge_by_id import merge_by_id
from app.workflow.nodes.plan_diversity import plan_diversity
from app.workflow.nodes.repair_chinese import repair_chinese
from app.workflow.nodes.repair_english import repair_english
from app.workflow.nodes.repair_indonesian import repair_indonesian
from app.workflow.nodes.semantic_alignment_qa import semantic_alignment_qa
from app.workflow.nodes.start_translation import start_translation
from app.workflow.nodes.translate_chinese import translate_chinese
from app.workflow.nodes.translate_indonesian import translate_indonesian
from app.workflow.nodes.validate_chinese import validate_chinese
from app.workflow.nodes.validate_english import validate_english
from app.workflow.nodes.validate_indonesian import validate_indonesian
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.valid_status import ValidStatus

RECURSION_LIMIT = 200


def route_after_english_validation(state: LessonGeneratorState) -> ValidStatus:
    return state["valid_status"]


def route_after_chinese_validation(state: LessonGeneratorState) -> ValidStatus:
    return state["cn_valid_status"]


def route_after_indonesian_validation(state: LessonGeneratorState) -> ValidStatus:
    return state["id_valid_status"]


def route_after_semantic_qa(
    state: LessonGeneratorState,
) -> Literal[
    "repair_chinese",
    "repair_indonesian",
    "final_validation",
]:
    if state.get("chinese_failed_ids"):
        return "repair_chinese"

    if state.get("indonesian_failed_ids"):
        return "repair_indonesian"

    return "final_validation"


class LessonGenerator:
    """A workflow that generates multilingual lesson sentences."""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        """Multilingual (EN/CN/ID) lesson generator workflow."""

        builder = StateGraph(
            state_schema=LessonGeneratorState,
            context_schema=BasicWorkflowContext,
        )

        # English generation
        builder.add_node("initialize_request", initialize_request)
        builder.add_node("plan_diversity", plan_diversity)
        builder.add_node("generate_english", generate_english)
        builder.add_node("validate_english", validate_english)
        builder.add_node("repair_english", repair_english)

        # Translation
        builder.add_node("start_translation", start_translation)

        builder.add_node("translate_chinese", translate_chinese)
        builder.add_node("validate_chinese", validate_chinese)
        builder.add_node("repair_chinese", repair_chinese)

        builder.add_node("translate_indonesian", translate_indonesian)
        builder.add_node("validate_indonesian", validate_indonesian)
        builder.add_node("repair_indonesian", repair_indonesian)

        # Merge / QA
        # merge_by_id joins the two translation branches, so it must wait until
        # every other branch has settled before it runs.
        builder.add_node("merge_by_id", merge_by_id, defer=True)
        builder.add_node("semantic_alignment_qa", semantic_alignment_qa)
        builder.add_node("final_validation", final_validation)

        # Entry
        builder.add_edge(START, "initialize_request")
        builder.add_edge("initialize_request", "plan_diversity")
        builder.add_edge("plan_diversity", "generate_english")

        # English generation loop
        builder.add_edge("generate_english", "validate_english")
        builder.add_edge("repair_english", "validate_english")
        builder.add_conditional_edges(
            "validate_english",
            route_after_english_validation,
            {
                ValidStatus.FAIL: "repair_english",
                ValidStatus.PENDING_BATCH: "generate_english",
                ValidStatus.SUCCESS: "start_translation",
            },
        )

        # Parallel translation: the validated English source fans out into
        # independent translation branches.
        builder.add_edge("start_translation", "translate_chinese")
        builder.add_edge("translate_chinese", "validate_chinese")
        builder.add_edge("repair_chinese", "validate_chinese")
        builder.add_conditional_edges(
            "validate_chinese",
            route_after_chinese_validation,
            {
                ValidStatus.FAIL: "repair_chinese",
                ValidStatus.SUCCESS: "merge_by_id",
            },
        )

        builder.add_edge("start_translation", "translate_indonesian")
        builder.add_edge("translate_indonesian", "validate_indonesian")
        builder.add_edge("repair_indonesian", "validate_indonesian")
        builder.add_conditional_edges(
            "validate_indonesian",
            route_after_indonesian_validation,
            {
                ValidStatus.FAIL: "repair_indonesian",
                ValidStatus.SUCCESS: "merge_by_id",
            },
        )

        # Merge the two branches back into one: id alignment.
        builder.add_edge("merge_by_id", "semantic_alignment_qa")
        builder.add_conditional_edges(
            "semantic_alignment_qa",
            route_after_semantic_qa,
            {
                "repair_chinese": "repair_chinese",
                "repair_indonesian": "repair_indonesian",
                "final_validation": "final_validation",
            },
        )

        builder.add_edge("final_validation", END)

        return builder.compile()

    def _build_initial_state(
        self,
        input: LessonGenerationRequest,
    ) -> LessonGeneratorState:
        
        return LessonGeneratorState(
            topic=input.topic,
            difficulty=input.difficulty,
            target_count=input.count,
            batch_size=input.batch_size,
            existing_english_sentences=input.existing_english_sentences,
        )

    def _build_context(
        self,
        llm_config: LLMConfig,
        user_id: str,
    ) -> BasicWorkflowContext:
        
        return BasicWorkflowContext(
            user_id=user_id,
            llm_runtime=LLMRuntime(config=llm_config),
        )

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
            input=self._build_initial_state(input),
            context=self._build_context(llm_config, user_id),
            config={"recursion_limit": RECURSION_LIMIT},
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
            input=self._build_initial_state(input),
            context=self._build_context(llm_config, user_id),
            config={"recursion_limit": RECURSION_LIMIT},
        )

        return final_state["final_items"]
