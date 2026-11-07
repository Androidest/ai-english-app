from langgraph.runtime import Runtime

from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_batch_ids, 
    validate_batch_sentence,
)

SYS_PROMPT_TEMPLATE = """You are an expert {source_language} learning content generator.
Generate a batch of {source_language} sentences accoding to the given requirements, and the given batch of unique IDs.

Hard requirements:
- Generate exactly one {source_language} sentence (item val) for every supplied immutable unique ID (item uid).
- Treat each uid only as keys and preserve them exactly. Never create, delete, rename, or modify a uid.
- Return each sentence along with each uid accoding to the ouput format.
- Sentences must be natural, grammatical, concise, and appropriate for the requested learner difficulty.
- Stay on the requested topic.
- Follow the given diversity plan for the next batch.
- Avoid duplicates.
- Avoid close semantic paraphrases of previously generated sentences.
- Avoid repeatedly using the same sentence-opening template.
- The topic description may be in any language, but the output language of the sentences MUST BE STRICTLY in '{source_language}'.
- Do not generate sentences in languages other than {source_language}.
- Return only the structured output. Do not add explanations or commentary.

Target language:
{source_language}

Maximum length of target sentences:
{source_max_len}

Topic:
{topic}

Learner Difficulty (CEFR level):
{difficulty}

Previously generated sentences:
{previous_sentences}

Diversity plan for the next batch:
{batch_plan}

Next batch of unique IDs that MUST be returned:
{batch_ids}

Generate the next {source_language} source batch, exactly {batch_count} items. 
"""

def get_latest_sentences(
    src_batches:list[SentenceBatch],
    count:int
) -> list[str]:

    sentences: list[str] = []
    for batch in reversed(src_batches):
        for item in reversed(batch.items):
            sentences.append(item.val)
            count -= 1
            if count <= 0:
                return sentences
    return sentences


def gen_src_batch(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Generate the next batch of source sentences according to:
        - The given language.
        - Topic.
        - difficulty
        - diversity plan
    """

    request = state["request"]
    src_batches = state["src_batches"]
    next_batch_idx = len(src_batches)
    batch_ids = state["target_ids_batches"][next_batch_idx]
    batch_plan = state["diversity_plan_batches"][next_batch_idx]

    batch_ids_txt = "\n".join(
        f'- uid="{uid}"'
        for uid in batch_ids
    )

    batch_plan_txt = "\n".join(
        f"- {bucket.category}: {bucket.count} items; {bucket.desc}"
        for bucket in batch_plan.buckets
    )

    previous_sentences_txt = "\n".join(
        f"- {sentence}" 
        for sentence in get_latest_sentences(src_batches, count=60)
    )

    def verify_cb(o: SentenceBatch):
        ok, reason = validate_batch_ids(
            expected_batch_ids=batch_ids,
            actual_batch=o,
        )

        if not ok:
            raise Exception(reason)

        ok, reason = validate_batch_sentence(
            batch=o,
            max_len=request.source_max_len,
            prompt_max_len=request.get_src_max_len_for_prompt(),
        )

        if not ok:
            raise Exception(reason)


    llm = runtime.context.llm_runtime.get_model(
        temperature=0.9,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=SentenceBatch,
        verify_cb=verify_cb,
        max_retries=5,
        keep_all_errors=True,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        source_language=request.source_language,
        source_max_len=request.get_src_max_len_for_prompt(),
        topic=request.topic,
        difficulty=request.difficulty,
        batch_plan=batch_plan_txt,
        batch_ids=batch_ids_txt,
        previous_sentences=(
            previous_sentences_txt
            or "(none)"
        ),
        batch_count=len(batch_ids),
    )

    result:SentenceBatch = llm.invoke(
        input=sys_prompt,
    )

    return LessonGeneratorState(
        src_batches=src_batches + [result],
    )
