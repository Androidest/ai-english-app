from langgraph.runtime import Runtime

from app.workflow._commons_.context import BasicWorkflowContext
from app.workflow._commons_.runnable import ConstrainedOutputWithRetry
from app.workflow.nodes._common import map_by_id, validate_ids, validate_translation_text
from app.workflow.schemas.translation import TranslationBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState

SYS_PROMPT_TEMPLATE = """You are a professional translator for an English-learning application.

Translate every supplied English source sentence into the requested target
language.

Hard requirements:
- Preserve every record_id exactly.
- Return exactly one translation for every supplied record_id.
- Never create, delete, rename, or modify a record_id.
- Translate directly from the English source sentence.
- Preserve the original meaning.
- Preserve negation.
- Preserve tense/aspect meaning.
- Preserve modality.
- Preserve numbers and quantities.
- Preserve dates and times.
- Preserve names and named entities.
- Do not omit meaningful information.
- Do not add information that does not exist in the source.
- Use natural target-language grammar.
- Return only structured translation items.

For Chinese:
- Use natural Simplified Chinese.
- Do not mechanically translate word-by-word.

For Indonesian:
- Use standard Bahasa Indonesia.
- Do not switch to Malaysian Malay.
- Avoid slang unless requested.
- Prefer natural expressions suitable for language learners.

Target language: Standard Bahasa Indonesia.

Translate every source item into standard Bahasa Indonesia.

Source items:
{source_items}

Return exactly one translation for every record_id.

Additional requirements:
- Use standard Bahasa Indonesia.
- Do not use Malaysian Malay.
- Preserve all semantic information from English.
"""


def translate_indonesian(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    """Node: Translate the validated English source into Indonesian."""
    english_map = map_by_id(
        state["english_items"]
    )

    source_items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
        }
        for record_id in state["target_ids"]
    ]

    def verify_cb(o: TranslationBatch):
        ok, reason = validate_ids(
            expected_ids=state["target_ids"],
            actual_ids=[
                item.record_id
                for item in o.items
            ],
        )

        if not ok:
            raise Exception(
                f"Indonesian structured-output alignment failure: {reason}"
            )

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.4,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=TranslationBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        source_items=source_items,
    )

    result = llm.invoke(
        input=sys_prompt,
    )

    failures = validate_translation_text(
        result.items
    )

    return LessonGeneratorState(
        indonesian_items=result.items,
        indonesian_failed_ids=sorted(
            failures.keys()
        ),
        errors=[
            f"Indonesian translation validation: "
            f"{record_id}: {reason}"
            for record_id, reason
            in failures.items()
        ],
    )
