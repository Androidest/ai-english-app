"""Deterministic helpers and business rules shared by the workflow nodes.

Nothing in this module calls an LLM: the helpers implement the validation and
bookkeeping rules of the lesson generation workflow.

Note: `runtime.context` is used to obtain the LLM runtime, but it must not be
forwarded to the chat model as an invoke kwarg, because it would be serialized
into the provider request payload.
"""

from __future__ import annotations

import os
import re
import uuid
from typing import TypeVar

from pydantic import BaseModel

from app.workflow.schemas.english_sentence import EnglishSentence
from app.workflow.schemas.translation import TranslationItem

DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))

MAX_ENGLISH_RETRIES = int(os.getenv("MAX_ENGLISH_RETRIES", "5"))
MAX_TRANSLATION_RETRIES = int(os.getenv("MAX_TRANSLATION_RETRIES", "5"))

MIN_ENGLISH_LENGTH = 3
MAX_ENGLISH_LENGTH = 500

MIN_TRANSLATION_LENGTH = 1
MAX_TRANSLATION_LENGTH = 1000

ModelT = TypeVar("ModelT", bound=BaseModel)


def create_record_id(index: int) -> str:
    """Create the application-generated immutable key.

    The LLM is never asked to create these ids.
    """
    return f"sentence_{index:05d}_{uuid.uuid4().hex[:8]}"


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def map_by_id(items: list[ModelT]) -> dict[str, ModelT]:
    return {item.record_id: item for item in items}


def validate_ids(
    expected_ids: list[str],
    actual_ids: list[str],
) -> tuple[bool, str]:
    """Validate that the LLM returned exactly the requested record ids."""
    if len(actual_ids) != len(expected_ids):
        return (
            False,
            f"Expected {len(expected_ids)} items, got {len(actual_ids)}.",
        )

    if len(set(actual_ids)) != len(actual_ids):
        return False, "Duplicate record_id detected."

    if set(actual_ids) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(actual_ids))
        extra = sorted(set(actual_ids) - set(expected_ids))

        return (
            False,
            f"record_id mismatch. missing={missing}, extra={extra}",
        )

    return True, ""


def validate_english_text(
    items: list[EnglishSentence],
) -> dict[str, str]:
    """Basic deterministic checks for the generated English sentences."""
    failures: dict[str, str] = {}

    for item in items:
        text = item.english.strip()

        if len(text) < MIN_ENGLISH_LENGTH:
            failures[item.record_id] = "English sentence is too short."
            continue

        if len(text) > MAX_ENGLISH_LENGTH:
            failures[item.record_id] = "English sentence is too long."
            continue

        if "\n" in text:
            failures[item.record_id] = "English item contains multiple lines."
            continue

        if "。" in text or "，" in text or "、" in text:
            failures[item.record_id] = (
                "English item contains obvious CJK punctuation."
            )

    return failures


def validate_translation_text(
    items: list[TranslationItem],
) -> dict[str, str]:
    """Basic deterministic checks for the generated translations."""
    failures: dict[str, str] = {}

    for item in items:
        text = item.text.strip()

        if len(text) < MIN_TRANSLATION_LENGTH:
            failures[item.record_id] = "Translation is empty."
            continue

        if len(text) > MAX_TRANSLATION_LENGTH:
            failures[item.record_id] = "Translation is unexpectedly long."

    return failures


def remaining_english_ids(
    target_ids: list[str],
    english_items: list[EnglishSentence],
    batch_size: int,
) -> list[str]:
    """Return the next batch of record ids that still need an English source."""
    completed = {item.record_id for item in english_items}

    remaining = [
        record_id
        for record_id in target_ids
        if record_id not in completed
    ]

    return remaining[:batch_size]


def semantic_duplicate_ids(
    candidates: list[EnglishSentence],
    comparison_sentences: list[str],
) -> set[str]:
    """Return candidate ids that are semantic duplicates.

    Semantic de-duplication is disabled, mirroring the legacy workflow where
    the embedding-based check was short-circuited and always returned an empty
    set.
    """
    # TODO: enable embedding-based duplicate detection against
    # `comparison_sentences` and between `candidates`.
    return set()
