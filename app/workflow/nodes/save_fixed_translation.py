from langgraph.runtime import Runtime
from langgraph.types import Overwrite
import copy

from app.workflow.states.lesson_generator_state import LessonGeneratorState
from app.workflow._core_.context import BasicWorkflowContext

    
def save_fixed_translation(
    state: LessonGeneratorState,
    runtime: Runtime[BasicWorkflowContext],
) -> LessonGeneratorState:
    
    """
    Node: Save the current translations to a dictionary according to the language.
    """

    lang_dict = state["translations_dict"]
    lang_idx = len(lang_dict)
    language = state["request"].translation_languages[lang_idx]
    translation = copy.deepcopy(state["translated_batches"])

    new_lang_dict = { **lang_dict, f"{language}": translation }

    return { 
        "translations_dict": new_lang_dict,
        "pending_batches": Overwrite([]),
    }
