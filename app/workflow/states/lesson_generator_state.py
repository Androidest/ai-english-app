from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.workflow.schemas.diversity_plan import DiversityPlan
from app.workflow.schemas.english_sentence import EnglishSentence
from app.workflow.schemas.translation import TranslationItem
from app.workflow.states.valid_status import ValidStatus


class LessonGeneratorState(TypedDict, total=False):
    """State of the multilingual lesson generation workflow."""

    # User request
    topic: str
    difficulty: str
    target_count: int
    batch_size: int
    existing_english_sentences: list[str]

    # Application-generated immutable record ids
    target_ids: list[str]

    # Diversity planning
    diversity_plan: DiversityPlan

    # Canonical English source
    english_items: list[EnglishSentence]

    # Current source-generation batch
    current_english_batch_ids: list[str]

    # Translation branches
    chinese_items: list[TranslationItem]
    indonesian_items: list[TranslationItem]

    # Routing statuses
    valid_status: ValidStatus
    cn_valid_status: ValidStatus
    id_valid_status: ValidStatus

    # Records that failed basic validation and need repair
    english_failed_ids: list[str]
    chinese_failed_ids: list[str]
    indonesian_failed_ids: list[str]

    # Retry counters
    english_retry_count: int
    chinese_retry_count: int
    indonesian_retry_count: int

    # Final output
    final_items: list[dict[str, str]]

    # Diagnostics. Written by several nodes (some in parallel), so it is
    # append-only.
    errors: Annotated[list[str], operator.add]
