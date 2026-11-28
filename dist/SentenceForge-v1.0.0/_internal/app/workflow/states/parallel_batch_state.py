from typing import Annotated, TypedDict

from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.states.lesson_generator_state import LessonGeneratorState 


class ParallelBatchState(TypedDict, total=False):
    """Local state for the parallel fanned-out nodes."""

    batch_id: int
    batch: SentenceBatch
    main_state: LessonGeneratorState
    language: str