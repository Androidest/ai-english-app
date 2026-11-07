from langgraph.runtime import Runtime
import re

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext
from app.workflow.schema_handlers.sentence_batch_handler import extract_uid_sentence_map


def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def final_merge_by_uid(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:

    """
    Node: Join all the language branches by the immutable uid, including the source and the translations
    """

    src_lang = state["request"].source_language
    src_batches = state["src_batches"]
    translations_dict = state["translations_dict"]

    # Map all the source sentences in to a dictionary by uid.
    src_map = extract_uid_sentence_map(src_batches)

    # Map all the translation sentences within each language in to a dictionary by uid.
    # Then store them into a bigger dictionary with the language as the key.
    trans_maps = { 
        lang: extract_uid_sentence_map(trans) 
        for lang, trans in translations_dict.items() 
    }

    final_items: list[dict[str, str]] = []
    # Use the sources uid to search for their translations 
    for uid, src in src_map.items():
        item = { src_lang: normalize_text(src) }
        for lang, trans in trans_maps.items():
            if uid not in trans:
                raise ValueError(f"Cannot find the {lang} translation for the source '{uid}':{src}")
            
            item[lang] = normalize_text(trans[uid]) # align and merge

        final_items.append(item)

    return LessonGeneratorState(
        final_items=final_items,
    )
