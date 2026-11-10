from langgraph.runtime import Runtime
from langgraph.types import Send

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_sentence_batch_uids,
    validate_batch_sentence,
)


SYS_PROMPT_TEMPLATE = """You are an expert content translator.
"Translate every supplied source sentence into the supplied target language."

Hard requirements:
- Generate exactly one translated sentence per UID.
- Treat the UIDs as keys; preserve them exactly as supplied. Never create, delete, rename, or modify a UID.
- Output only structured translation data. Do not add extra explanations, commentary, or preamble.
- Do not mechanically translate word-by-word.
- Do not make duplicate sentences.
- Do not copy directly from the supplied sentences. 
- Do not omit meaningful information from the source.
- Do not add information that does not exist in the source.
- Use natural grammar and expressions, but do not deviate far from the original intent.
- Preserve the following as closely as possible:
    1. the original meaning.
    2. negation.
    3. tense/aspect meaning.
    4. modality.
    5. numbers and quantities.
    6. dates and times.
    7. names and named entities.
    8. Tone
    9. Semantic intent
    10. Causal relationship

Source language:
{src_language}

Source sentences:
{src_sentences_txt}

Translate source into the target language:
{target_language}
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
    batch_sentences_txt = batch.model_dump_json(indent=2)

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
        temperature=1.3,
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

    return LessonGeneratorState(
        pending_batches={ batch_id: result },
    ) 
