from langgraph.runtime import Runtime
from langgraph.types import Send

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow.states.parallel_batch_state import ParallelBatchState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow._core_.runnable import ConstrainedOutputWithRetry
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schema_handlers.sentence_batch_handler import (
    validate_batch_ids,
    validate_batch_sentence,
    merge_batch,
)

SYS_PROMPT_TEMPLATE = """You are an expert {language} learning content grammar fixer.
Repair only the sentences with grammar errors.

Hard requirements:
- Update only the sentences with grammar errors. If nothing is to be updated, return the 'items' with empty list.
- Do not copy from the supplied sentences. If a sentence is grammatically correct do not return it.
- Preserve every uid exactly.
- Generate exactly one repaired sentence per uid.
- Do not duplicate another supplied sentence.
- Return only structured output. Do not add explanations or commentary.
- Preserve all of the following whenever possible from the original text:
    1. Original meaning
    2. Tone
    3. Vocabulary difficulty level
    4. Sentence length
    5. Semantic intent

Target language:
{language}

Check the below {language} sentences for grammar error and fix them:
{batch_sentences}

Return only the updated items.
"""


def fanout_fix_grammar_batch(
    node: str,
    state: ParallelBatchState,
) -> list[Send]:
    
    """
    To fan-out the 'fix_grammar_batch' node into namy parallel nodes to proccess all the batches.
    """
    
    return [
        Send(
            node=node,
            arg=ParallelBatchState(
                batch_idx=idx,
                batch=state["src_batches"][idx],
                main_state=state,
                language=state["request"].source_language,
            ) # local state
        )
        for idx in range(len(state["src_batches"]))
    ]


def fix_grammar_batch(
    state: ParallelBatchState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Check and repair the problematic sentences.
    """

    # local state
    batch = state["batch"]
    language = state["language"]

    batch_ids = set(item.uid for item in batch.items)
    batch_sentences_txt = batch.model_dump_json(indent=2)

    def verify_cb(o: SentenceBatch):

        if len(o.items) == 0:
            return # nothing is to be updated

        ok, reason = validate_batch_ids(
            expected_batch_ids=batch_ids,
            actual_batch=o,
            check_missing=False, # Do not check for missing IDs because only the problematic sentences will be fixed, not all.
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
        temperature=0.5,
    )

    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=SentenceBatch,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=False,
    )

    sys_prompt = SYS_PROMPT_TEMPLATE.format(
        language=language,
        batch_sentences=batch_sentences_txt,
    )

    result:SentenceBatch = llm.invoke(
        input=sys_prompt,
    )
    
    merged_batch = merge_batch(
        base=batch, 
        updates=result
    )

    return LessonGeneratorState(
        pending_batches=[merged_batch],
    ) 


