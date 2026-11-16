from langgraph.runtime import Runtime
from langgraph.config import get_stream_writer
from langgraph.types import Send

from app.workflow.schema_handlers.commons import item_to_text
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow.states.stream_data import StreamData
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_sentence_batch_uids,
    validate_batch_sentence,
)


SYS_PROMPT_TEMPLATE = """You are an expert content translator.
Translate every supplied source sentence into the supplied target language.

Hard requirements:
- Generate exactly one translated sentence per UID.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured translation data. Do not add extra explanations, commentary, or preamble.
- Do not make duplicate sentences.
- Do not copy directly from the supplied sentences.
- Do not omit meaningful information from the source in the translation.
- Do not add information to the translation that is not present in the source.
- The translation should not deviate from the original intent.
- The translation shall take the logic and expression of the source sentence as its baseline and render faithfully, even if the source contains errors.
- Prefer a faithful, literal rendering over stylistic variation. Do not introduce synonyms, rephrase for elegance, or add/remove surface details unless a literal rendering is unintelligible in the target language.
- If a minimal adjustment is needed for grammaticality, keep it minimal and preserve the source's surface meaning.
- Each translation shall preserve all of the following with its source sentence:
    1. Semantic intent
    2. The original meaning
    3. Negation
    4. Tense/aspect meaning
    5. Modality
    6. Numbers and quantities
    7. Dates and times
    8. Names and named entities
    9. Tone
    10. Causal relationship
    11. Wording style
- For culture-specific items (food, dishes, places, institutions, festivals, measures, titles, brands):
    1. Replace a non-established literal calque with the commonly accepted rendering in the target language if one exists; 
    2. If none exists, use a transliteration in the target language's script, optionally with a brief category word. 
    3. Do not substitute one established variant for another; 

Target translation language:
{target_language}

Source language:
{src_language}

Source sentences:
{src_sentences_txt}
"""


def fanout_translation(
    node: str,
    state: LessonGeneratorState
) -> list[Send]:
    
    """
    To fan-out the 'translate_src_batch' node into namy parallel nodes to proccess all the batches.
    """

    request = state["request"]
    src_batches = state["src_batches"]
    lang_idx = len(state["translations_dict"])

    return [
        Send(
            node=node, # fan-out into multi-parallel node
            arg=ParallelBatchState(
                batch_id=idx,
                batch=src_batches[idx],
                main_state=state,
                language=request.translation_languages[lang_idx],
            ) # local state
        )
        for idx in range(len(src_batches))
    ]


def translate_src_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Translate the source sentences into the target language.
    """

    # local state
    batch_id = state["batch_id"]
    batch = state["batch"]
    target_language = state["language"]
    main_state = state["main_state"]
    src_language = main_state["request"].source_language

    batch_ids = set(item.uid for item in batch.items)
    batch_sentences_txt = item_to_text(batch)

    def verify_cb(o: SentenceBatch):
    
        ok, reason = validate_sentence_batch_uids(
            expected_uids=batch_ids,
            actual_batch=o
        )

        if not ok:
            raise Exception(reason)

        ok, reason = validate_batch_sentence(
            batch=o,
            max_len=999, # max length not needed
            prompt_max_len=999,
        )

        if not ok:
            raise Exception(reason)

    llm = runtime.context.llm_runtime.get_model(
        temperature=0.1,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=SentenceBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=False,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        src_language=src_language,
        src_sentences_txt=batch_sentences_txt,
        target_language=target_language,
    )

    result: SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    writer = get_stream_writer()
    writer(StreamData(
        type=f"trans_{target_language}",
        processed_count=len(result.items),
    ))

    return {
        "pending_batches": { batch_id: result },
    }
