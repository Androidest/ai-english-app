from app.workflow.states.lesson_generator_state import LessonGeneratorState


def start_translation(state: LessonGeneratorState) -> LessonGeneratorState:
    """Node: Fan-out marker before the parallel translation branches."""
    return LessonGeneratorState()
