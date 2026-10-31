from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.nodes._common import (
    DEFAULT_BATCH_SIZE,
    remaining_english_ids,
    semantic_duplicate_ids,
    validate_ids,
)
from app.workflow.schemas.english_sentence import EnglishBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are an expert English-learning content generator.

Generate English source sentences only.

Hard requirements:
- Return exactly one item for every supplied record_id.
- Preserve every record_id exactly.
- Never create, delete, rename, or modify a record_id.
- Generate exactly one English sentence per item.
- Every English field must contain exactly one sentence.
- Sentences must be natural, grammatical, concise, and appropriate for the
  requested learner difficulty.
- Stay on the requested topic.
- Follow the diversity plan.
- Avoid duplicates.
- Avoid close semantic paraphrases of previously generated sentences.
- Avoid repeatedly using the same sentence-opening template.
- Do not generate Chinese.
- Do not generate Indonesian.
- Do not add explanations or commentary.

The application has already generated the immutable record IDs.
Treat them only as keys and preserve them exactly.

Generate the next English source batch.

Topic:
{topic}

Difficulty:
{difficulty}

Diversity plan:
{plan_text}

Immutable record IDs that MUST be returned:
{requested_ids}

Previously generated English sentences:
{previous_context}

Generate exactly {batch_count} items.

Do not repeat or closely paraphrase the previous sentences.
Return exactly one English sentence for every supplied record_id.
"""


def generate_english(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Generate the next batch of English source sentences."""
    target_ids = state["target_ids"]

    batch_ids = remaining_english_ids(
        target_ids=target_ids,
        english_items=state["english_items"],
        batch_size=state.get(
            "batch_size",
            DEFAULT_BATCH_SIZE,
        ),
    )

    if not batch_ids:
        return LessonGeneratorState(
            current_english_batch_ids=[],
        )

    plan_text = "\n".join(
        (
            f"- {bucket.category}: "
            f"{bucket.count} items; "
            f"{bucket.description}"
        )
        for bucket in state["diversity_plan"].buckets
    )

    previous = (
        state.get("existing_english_sentences", [])
        + [
            item.english
            for item in state["english_items"]
        ]
    )

    previous_context = "\n".join(
        f"- {sentence}"
        for sentence in previous[-60:]
    )

    requested_ids = "\n".join(
        f'- record_id="{record_id}"'
        for record_id in batch_ids
    )

    def verify_cb(o: EnglishBatch):
        ok, reason = validate_ids(
            expected_ids=batch_ids,
            actual_ids=[
                item.record_id
                for item in o.items
            ],
        )

        if not ok:
            raise Exception(
                f"English structured-output alignment failure: {reason}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.8,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=EnglishBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        topic=state["topic"],
        difficulty=state["difficulty"],
        plan_text=plan_text,
        requested_ids=requested_ids,
        previous_context=(
            previous_context
            or "(none)"
        ),
        batch_count=len(batch_ids),
    )

    result = llm.invoke(
        input=sys_prompt,
    )

    semantic_duplicates = semantic_duplicate_ids(
        candidates=result.items,
        comparison_sentences=previous,
    )

    if semantic_duplicates:
        # Remove only the rejected candidates from the current batch.
        result.items = [
            item
            for item in result.items
            if item.record_id
            not in semantic_duplicates
        ]

    return LessonGeneratorState(
        english_items=(
            state["english_items"]
            + result.items
        ),
        current_english_batch_ids=batch_ids,
        english_failed_ids=[
            record_id
            for record_id in batch_ids
            if record_id in semantic_duplicates
        ],
        errors=[
            f"Semantic duplicate rejected: {record_id}"
            for record_id in semantic_duplicates
        ],
    )
