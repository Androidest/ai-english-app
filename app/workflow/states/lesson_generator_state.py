from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.utils.types import Language
from app.workflow.schemas.diversity_plan import DiversityPlan
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schemas.issue_batch import IssueBatch
from app.workflow.schemas.issue_correction_request import IssueCorrectionRequest
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest

def merge_batches(
    left: dict[str, SentenceBatch],
    right: dict[str, SentenceBatch],
) -> dict[str, SentenceBatch]:
    return {**left, **right}

class LessonGeneratorState(TypedDict, total=False):
    """State of the multilingual lesson generation workflow."""

    # User request
    request: LessonGenerationRequest

    # ------ Source generation --------
    # Application-generated immutable record ids
    target_ids: list[str]
    target_ids_batches: list[set[str]] # batchified ids

    # Diversity planning
    diversity_plan: DiversityPlan
    diversity_plan_batches: list[DiversityPlan] # batchified plan

    # The canonical source of trust. 
    src_batches: dict[str, SentenceBatch] # key: batch id, value: batch
    previous_sentences: list[str]

    # ------------ Issue correction ---------
    # This request need to be assigned before the subgrpah starts processing. 
    issue_correction_request: IssueCorrectionRequest
    # Marks which batches are in process. It will decrease if some of the batches finish processing.
    processing_batch_ids: list[str]
    remaining_attempts: int
    # Temporally batches: They gather the results from fanned-out multi-parallel nodes after they fan in.
    issue_batches: Annotated[dict[str, IssueBatch], merge_batches] # Use 'Annotated' to add a reducer to it for parallel update.
    corrected_batches: Annotated[dict[str, SentenceBatch], merge_batches]

    # ------ Temporally batches --------
    pending_batches: Annotated[dict[str, SentenceBatch], merge_batches] # a pending result waiting for later merging.

    # ------ Translation --------
    # translated from the canonical source of trust. 
    translated_batches: dict[str, SentenceBatch]
    # Store all translations in different languages. 
    translations_dict: dict[str, dict[str, SentenceBatch]] # The keys are the languages, values are the batches.
    
    # ------- Final output --------
    # Every list item is a set of sentences, including the source and its translations.
    final_items: list[dict[str, str]] # The keys of the dictionaries are the the languages, values are the sentences.

    pending_logs: Annotated[list[str], operator.add]
    logs: list[str]