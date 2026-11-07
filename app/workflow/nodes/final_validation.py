from langgraph.runtime import Runtime

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schema_handlers.sentence_batch_handler import normalize_text
from app.workflow.schemas.final_qa import FinalQA
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a strict final dataset validator.

Validate the final multilingual dataset.

The final dataset must satisfy:
- Exactly the requested number of records.
- Every record has a non-empty EN field.
- Every record has a non-empty CN field.
- Every record has a non-empty ID field.
- Every English sentence is unique.
- No field contains obvious placeholder text.
- The number of records is exactly correct.

Do not rewrite any item.
Return only the structured validation result.

Requested count:
{target_count}

Final dataset:
{final_items}

Validate the final dataset.
"""


def final_validation(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Deterministically and semantically validate the final dataset."""
    final_items = state["final_items"]
    target_count = state["target_count"]

    # Deterministic validation first.
    if len(final_items) != target_count:
        raise ValueError(
            f"Final count mismatch: expected {target_count}, "
            f"got {len(final_items)}."
        )

    if any(
        not item.get("EN", "").strip()
        or not item.get("CN", "").strip()
        or not item.get("ID", "").strip()
        for item in final_items
    ):
        raise ValueError(
            "Final dataset contains an empty EN/CN/ID field."
        )

    english_values = [
        normalize_text(item["EN"])
        for item in final_items
    ]

    if len(set(english_values)) != target_count:
        raise ValueError(
            "Final dataset contains duplicate English sentences."
        )

    def verify_cb(o: FinalQA):
        if not o.valid:
            raise Exception(
                f"Final LLM validation failed: {o.reason}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.1,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=FinalQA,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        target_count=target_count,
        final_items=final_items,
    )

    llm.invoke(
        input=sys_prompt,
    )

    return LessonGeneratorState()
