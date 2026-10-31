from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.diversity_plan import DiversityPlan
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a senior English-learning content planner.

Your task is to create a compact diversity plan for generating a requested
number of English source sentences.

The English sentences will later be translated into Chinese and Indonesian.
The English sentence is the canonical source of truth.

Goals:
- Maximize semantic diversity.
- Maximize scenario diversity.
- Maximize speech-act diversity.
- Vary grammatical structures naturally.
- Vary vocabulary, sentence openings, subjects, verbs, and objects.
- Avoid generating many paraphrases of one underlying meaning.
- Stay strictly within the requested topic and learner difficulty.
- Make all buckets concrete and useful for downstream generation.

Do not generate actual English sentences.
Do not generate translations.

The sum of all bucket counts MUST equal the requested total count.
Return only the structured output.

Topic:
{topic}

Learner difficulty:
{difficulty}

Requested total sentence count:
{target_count}

Create a diversity plan containing multiple useful categories.

The sum of bucket counts MUST equal exactly {target_count}.

Do not write actual sentences.
"""


def plan_diversity(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Plan the diversity of the English source sentences."""
    topic = state["topic"]
    difficulty = state["difficulty"]
    target_count = state["target_count"]

    def verify_cb(o: DiversityPlan):
        total = sum(
            bucket.count
            for bucket in o.buckets
        )

        if total != target_count:
            raise Exception(
                "Diversity planner returned an invalid count allocation: "
                f"{total} != {target_count}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.5,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=DiversityPlan,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        topic=topic,
        difficulty=difficulty,
        target_count=target_count,
    )

    plan = llm.invoke(
        input=sys_prompt,
    )

    return LessonGeneratorState(
        diversity_plan=plan,
    )
