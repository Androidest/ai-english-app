from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.utils.types import Language
from app.workflow.schemas.diversity_plan import DiversityPlan
from app.workflow.schemas.sentence_batch import SentenceBatch
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest


class LessonGeneratorState(TypedDict, total=False):
    """State of the multilingual lesson generation workflow."""

    # User request
    request: LessonGenerationRequest
    
    # Application-generated immutable record ids
    target_ids: list[str]

    # Diversity planning
    diversity_plan: DiversityPlan

    # batchified plan and ids
    target_ids_batches: list[set[str]]
    diversity_plan_batches: list[DiversityPlan]

    # The canonical source of trust. 
    src_batches: list[SentenceBatch]

    # It gathers the results from fanned-out multi-parallel nodes after they fan in.
    # Use 'Annotated' to add a reducer to it for parallel update.
    pending_batches: Annotated[list[SentenceBatch], operator.add] # a result pending for merging

    # translated from the canonical source of trust. 
    translated_batches: list[SentenceBatch]
    # Store all translations in different languages. 
    translations_dict: dict[str, list[SentenceBatch]] # The keys are the languages, values are the batches.
    
    # Final output
    # Every list item is a set of sentences, including the source and its translations.
    final_items: list[dict[str, str]] # The keys of the dictionaries are the the languages, values are the sentences.