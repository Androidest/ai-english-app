from langgraph.runtime import Runtime

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.diversity_plan import DiversityPlan
from app.workflow.schema_handlers.diversity_plan_handler import validate_plan
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a senior {source_language} learning content planner.
Your task is to create a compact diversity plan to guide the downstream generation of a requested number of {source_language} sentences.

Goals:
- Maximize semantic diversity.
- Maximize scenario diversity.
- Maximize speech-act diversity.
- Vary grammatical structures naturally as possible.
- Vary vocabulary, sentence openings, subjects, verbs, and objects.
- Avoid generating many paraphrases of one underlying meaning.
- Stay strictly within the requested topic and learner difficulty.

Hard requirements:
- Create a diversity plan containing multiple useful categories (buckets).
- Each bucket has a different category. Avoid repeatedly using the same category.
- Make all buckets concrete and useful for downstream sentence generation.
- Use more recognisable profesional terms as possible to make the downstream generation guidance (prompts) more compact and precise. 
- Do not generate actual {source_language} sentences.
- The sum of all bucket sentence counts MUST equal the requested total sentence count. However, the numbers of buckets can be smaller than the total sentence count.
- Return only the structured output. Do not add explanations or commentary.
- The topic description may be in any language, but the output language of the plan (guidance) MUST BE STRICTLY in English, including the categories and their descriptions.
- Take the expected maximum length of the sentences into account. If the guidance is too complicated, it will cause the downstream sentence generation to exceed the maximum length.

Topic:
{topic}

Learner difficulty (CEFR level):
{difficulty}

Requested total sentence count:
{target_count}

Expected maximum length of the sentences:
{source_max_len}
"""


def plan_diversity(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """Node: Plan the diversity of the source sentences."""

    request = state["request"]

    def verify_cb(o: DiversityPlan):
        ok, reason = validate_plan(o, request.target_count)
        if not ok:
            raise ValueError(reason)

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.7,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=DiversityPlan,
        verify_cb=verify_cb,
        max_retries=3,
        keep_all_errors=False,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        source_language=request.source_language,
        source_max_len=request.get_src_max_len_for_prompt(),
        topic=request.topic,
        difficulty=request.difficulty,
        target_count=request.target_count,
    )

    plan = llm.invoke(
        input=sys_prompt,
    )

    return {
        "diversity_plan": plan,
    }
