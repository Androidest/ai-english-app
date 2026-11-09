from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext

    
def save_translation(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Save the current translations to a dictionary according to the language.
    """

    translation_languages = state["request"].translation_languages
    lang_dict = state["translations_dict"]

    cur_lang_idx = len(lang_dict)
    cur_language = translation_languages[cur_lang_idx]
    cur_translation = copy.deepcopy(state["translated_batches"])

    new_lang_dict = { **lang_dict, f"{cur_language}": cur_translation }

    return { 
        "translations_dict": new_lang_dict,
    }
