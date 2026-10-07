from __future__ import annotations

import asyncio
import math
import os
import re
import uuid
from typing import Literal, TypedDict

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field
from app.prompts.prompts import * 
from typing import Annotated, Literal, TypedDict
import operator
from enum import Enum

# ============================================================================
# Configuration
# ============================================================================

MODEL_NAME = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
API_KEY = "sk-1c3d6fc60c2649a9bdcfa3982af93250"

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "text-embedding-3-small",
)

DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))

MAX_ENGLISH_RETRIES = int(os.getenv("MAX_ENGLISH_RETRIES", "5"))
MAX_TRANSLATION_RETRIES = int(os.getenv("MAX_TRANSLATION_RETRIES", "5"))
MAX_SEMANTIC_QA_RETRIES = int(os.getenv("MAX_SEMANTIC_QA_RETRIES", "3"))


class ValidStatus(Enum):
    SUCCESS = 'success'
    FAIL = 'fail'
    PENDING_BATCH = 'pending_batch'

# Semantic duplicate threshold.
#
# This should be calibrated on your own data instead of being treated as a
# universal threshold.
SEMANTIC_DUPLICATE_THRESHOLD = float(
    os.getenv("SEMANTIC_DUPLICATE_THRESHOLD", "0.90")
)

MIN_ENGLISH_LENGTH = 3
MAX_ENGLISH_LENGTH = 500

MIN_TRANSLATION_LENGTH = 1
MAX_TRANSLATION_LENGTH = 1000

# Enable semantic deduplication against:
#   1. sentences generated in the current request
#   2. externally supplied historical sentences
ENABLE_SEMANTIC_DEDUP = (
    os.getenv("ENABLE_SEMANTIC_DEDUP", "true").lower()
    in {"1", "true", "yes", "on"}
)



# ============================================================================
# LLM
# ============================================================================

generation_llm = ChatDeepSeek(
    model=MODEL_NAME,
    temperature=0.8,
    base_url=BASE_URL,
    api_key=API_KEY,
    extra_body={"thinking": {"type": "disabled"}},
)

translation_llm = ChatDeepSeek(
    model=MODEL_NAME,
    temperature=0.4,
    base_url=BASE_URL,
    api_key=API_KEY,
    extra_body={"thinking": {"type": "disabled"}},
)

qa_llm = ChatDeepSeek(
    model=MODEL_NAME,
    temperature=0.1,
    base_url=BASE_URL,
    api_key=API_KEY,
    extra_body={"thinking": {"type": "disabled"}},
)

planner_llm = ChatDeepSeek(
    model=MODEL_NAME,
    temperature=0.5,
    base_url=BASE_URL,
    api_key=API_KEY,
    extra_body={"thinking": {"type": "disabled"}},
)


# ============================================================================
# Structured Output Models
# ============================================================================

class DiversityBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    count: int = Field(ge=1)


class DiversityPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buckets: list[DiversityBucket] = Field(min_length=1)


class EnglishSentence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    english: str = Field(min_length=1)


class EnglishBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[EnglishSentence] = Field(min_length=1)


class TranslationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TranslationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TranslationItem] = Field(min_length=1)


class TranslationQAItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    chinese_ok: bool
    indonesian_ok: bool
    reason: str = Field(min_length=1)


class TranslationQABatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TranslationQAItem] = Field(min_length=1)


class FinalQA(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    reason: str = Field(min_length=1)


# ============================================================================
# Structured-Output LLM Wrappers
# ============================================================================

planner = planner_llm.with_structured_output(DiversityPlan)

english_generator = generation_llm.with_structured_output(EnglishBatch)
english_repair = generation_llm.with_structured_output(EnglishBatch)

translator = translation_llm.with_structured_output(TranslationBatch)
translation_repair = translation_llm.with_structured_output(TranslationBatch)

alignment_qa = qa_llm.with_structured_output(TranslationQABatch)
final_qa = qa_llm.with_structured_output(FinalQA)


# ============================================================================
# Optional Semantic Deduplication
# ============================================================================

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings

    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
        )

    return _embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


async def semantic_duplicate_ids(
    candidates: list[EnglishSentence],
    comparison_sentences: list[str],
) -> set[str]:

    return set() #TODO

    if not ENABLE_SEMANTIC_DEDUP:
        return set()

    if not candidates or not comparison_sentences:
        return set()

    texts = [item.english for item in candidates]

    embeddings = get_embeddings()

    candidate_vectors = await embeddings.aembed_documents(texts)
    existing_vectors = await embeddings.aembed_documents(
        comparison_sentences
    )

    duplicates: set[str] = set()

    for item, vector in zip(candidates, candidate_vectors):
        for existing_vector in existing_vectors:
            similarity = cosine_similarity(
                vector,
                existing_vector,
            )

            if similarity >= SEMANTIC_DUPLICATE_THRESHOLD:
                duplicates.add(item.record_id)
                break

    # Also compare candidates with one another.
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            similarity = cosine_similarity(
                candidate_vectors[i],
                candidate_vectors[j],
            )

            if similarity >= SEMANTIC_DUPLICATE_THRESHOLD:
                # Keep the earlier candidate and reject the later one.
                duplicates.add(candidates[j].record_id)

    return duplicates


# ============================================================================
# Workflow State
# ============================================================================

class WorkflowState(TypedDict, total=False):
    # User request
    topic: str
    difficulty: str
    target_count: int
    batch_size: int

    target_ids: list[str]

    # Previously generated content from earlier application runs.
    existing_english_sentences: list[str]

    # Diversity planning
    diversity_plan: DiversityPlan

    # Canonical English source
    english_items: list[EnglishSentence]

    # Current source-generation batch
    current_english_batch_ids: list[str]

    # Translation branches
    chinese_items: list[TranslationItem]
    indonesian_items: list[TranslationItem]

    # Validation state
    valid_status: ValidStatus
    cn_valid_status: ValidStatus
    id_valid_status: ValidStatus
    english_failed_ids:   Annotated[list[str], operator.add]
    chinese_failed_ids:   Annotated[list[str], operator.add]
    indonesian_failed_ids: Annotated[list[str], operator.add]

    # Retry counters
    english_retry_count: int
    chinese_retry_count: int
    indonesian_retry_count: int
    semantic_qa_retry_count: int

    # Final output
    final_items: list[dict[str, str]]

    # Errors / diagnostics
    errors: Annotated[list[str], operator.add]


# ============================================================================
# Utility Functions
# ============================================================================

def create_record_id(index: int) -> str:
    """
    Application-generated immutable key.

    Never ask the LLM to create these IDs.
    """
    return f"sentence_{index:05d}_{uuid.uuid4().hex[:8]}"

def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text

def map_by_id(items: list[BaseModel]) -> dict[str, BaseModel]:
    return {
        item.record_id: item
        for item in items
    }

def validate_ids(
    expected_ids: list[str],
    actual_ids: list[str],
) -> tuple[bool, str]:
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
            failures[item.record_id] = (
                "English item contains multiple lines."
            )
            continue

        # Conservative sanity checks.
        if "。" in text or "，" in text or "、" in text:
            failures[item.record_id] = (
                "English item contains obvious CJK punctuation."
            )

    return failures

def validate_translation_text(
    items: list[TranslationItem],
) -> dict[str, str]:
    failures: dict[str, str] = {}

    for item in items:
        text = item.text.strip()

        if len(text) < MIN_TRANSLATION_LENGTH:
            failures[item.record_id] = "Translation is empty."
            continue

        if len(text) > MAX_TRANSLATION_LENGTH:
            failures[item.record_id] = (
                "Translation is unexpectedly long."
            )

    return failures

def remaining_english_ids(
    target_ids: list[str],
    english_items: list[EnglishSentence],
    batch_size: int,
) -> list[str]:
    completed = {
        item.record_id
        for item in english_items
    }

    remaining = [
        record_id
        for record_id in target_ids
        if record_id not in completed
    ]

    return remaining[:batch_size]


# ============================================================================
# Node 1: Initialize
# ============================================================================

async def initialize_request(
    state: WorkflowState,
) -> WorkflowState:
    target_count = state["target_count"]

    if target_count <= 0:
        raise ValueError("target_count must be greater than 0.")

    batch_size = state.get(
        "batch_size",
        DEFAULT_BATCH_SIZE,
    )

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0.")

    target_ids = [
        create_record_id(i + 1)
        for i in range(target_count)
    ]

    return {
        "target_ids": target_ids,
        "english_items": [],
        "chinese_items": [],
        "indonesian_items": [],
        "current_english_batch_ids": [],
        "english_failed_ids": [],
        "chinese_failed_ids": [],
        "indonesian_failed_ids": [],
        "english_retry_count": 0,
        "chinese_retry_count": 0,
        "indonesian_retry_count": 0,
        "semantic_qa_retry_count": 0,
        "final_items": [],
        "errors": [],
    }


# ============================================================================
# Node 2: Diversity Planner
# ============================================================================

async def plan_diversity(
    state: WorkflowState,
) -> WorkflowState:
    target_count = state["target_count"]

    prompt = f"""
Topic:
{state["topic"]}

Learner difficulty:
{state["difficulty"]}

Requested total sentence count:
{target_count}

Create a diversity plan containing multiple useful categories.

The sum of bucket counts MUST equal exactly {target_count}.

Do not write actual sentences.
"""

    result = await planner.ainvoke(
        [
            (
                "system",
                DIVERSITY_PLANNER_SYSTEM,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    total = sum(
        bucket.count
        for bucket in result.buckets
    )

    if total != target_count:
        raise ValueError(
            "Diversity planner returned an invalid count allocation: "
            f"{total} != {target_count}"
        )

    return {
        "diversity_plan": result,
    }


# ============================================================================
# Node 3: Generate One English Batch
# ============================================================================

async def generate_english(
    state: WorkflowState,
) -> WorkflowState:
    target_ids = state["target_ids"]

    batch_ids = remaining_english_ids(
        target_ids=target_ids,
        english_items=state["english_items"],
        batch_size=state.get(
            "batch_size",
            DEFAULT_BATCH_SIZE,
        ),
    )

    if not batch_ids:
        return {
            "current_english_batch_ids": [],
        }

    plan_text = "\n".join(
        (
            f"- {bucket.category}: "
            f"{bucket.count} items; "
            f"{bucket.description}"
        )
        for bucket in state["diversity_plan"].buckets
    )

    previous = (
        state.get("existing_english_sentences", [])
        + [
            item.english
            for item in state["english_items"]
        ]
    )

    previous_context = "\n".join(
        f"- {sentence}"
        for sentence in previous[-60:]
    )

    requested_ids = "\n".join(
        f'- record_id="{record_id}"'
        for record_id in batch_ids
    )

    prompt = f"""
Generate the next English source batch.

Topic:
{state["topic"]}

Difficulty:
{state["difficulty"]}

Diversity plan:
{plan_text}

Immutable record IDs that MUST be returned:
{requested_ids}

Previously generated English sentences:
{previous_context or "(none)"}

Generate exactly {len(batch_ids)} items.

Do not repeat or closely paraphrase the previous sentences.
Return exactly one English sentence for every supplied record_id.
"""

    result = await english_generator.ainvoke(
        [
            (
                "system",
                ENGLISH_GENERATOR_SYSTEM,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=batch_ids,
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"English structured-output alignment failure: {reason}"
        )

    existing = previous

    semantic_duplicates = await semantic_duplicate_ids(
        candidates=result.items,
        comparison_sentences=existing,
    )

    if semantic_duplicates:
        # Remove only the rejected candidates from the current batch.
        result.items = [
            item
            for item in result.items
            if item.record_id
            not in semantic_duplicates
        ]

    return {
        "english_items": (
            state["english_items"]
            + result.items
        ),
        "current_english_batch_ids": batch_ids,
        "english_failed_ids": [
            item_id
            for item_id in batch_ids
            if item_id in semantic_duplicates
        ],
        "errors": [
                f"Semantic duplicate rejected: {record_id}"
                for record_id in semantic_duplicates
            ]
        ,
    }


# ============================================================================
# Node 4: Validate Current English Batch
# ============================================================================

async def validate_english(
    state: WorkflowState,
) -> WorkflowState:
    current_ids = set(
        state.get(
            "current_english_batch_ids",
            [],
        )
    )

    batch = [
        item
        for item in state["english_items"]
        if item.record_id in current_ids
    ]

    expected_ids = state["current_english_batch_ids"]

    actual_ids = [ item.record_id for item in batch ]

    failures: dict[str, str] = {}

    ok, reason = validate_ids(
        expected_ids=expected_ids,
        actual_ids=actual_ids,
    )

    if not ok:
        for record_id in expected_ids:
            failures[record_id] = reason

    text_failures = validate_english_text(batch)

    failures.update(text_failures)

    english_failed_ids = sorted(failures.keys())

    # routing for the conditional edges
    valid_status = ValidStatus.SUCCESS
    if len(english_failed_ids) > 0:
        valid_status = ValidStatus.FAIL
    elif len(state["english_items"]) < state["target_count"]:
        valid_status = ValidStatus.PENDING_BATCH

    return {
        "english_failed_ids": english_failed_ids,
        "valid_status": valid_status,
        "errors": [
                f"English validation: {record_id}: {reason}"
                for record_id, reason
                in failures.items()
            ]
        ,
    }

# ============================================================================
# Node 5: Repair Failed English Items
# ============================================================================

async def repair_english(
    state: WorkflowState,
) -> WorkflowState:
    failed_ids = state["english_failed_ids"]

    if not failed_ids:
        return {}

    retry_count = state.get(
        "english_retry_count",
        0,
    )

    if retry_count >= MAX_ENGLISH_RETRIES:
        raise RuntimeError(
            "Maximum English retry count exceeded for: "
            f"{failed_ids}"
        )

    current_map = map_by_id(
        state["english_items"]
    )

    failed_items = []

    for record_id in failed_ids:
        item = current_map.get(record_id)

        failed_items.append(
            {
                "record_id": record_id,
                "english": (
                    item.english
                    if item
                    else ""
                ),
            }
        )

    prompt = f"""
Topic:
{state["topic"]}

Difficulty:
{state["difficulty"]}

Repair these failed English records:

{failed_items}

Return exactly one repaired item for every record_id.
"""

    result = await english_repair.ainvoke(
        [
            (
                "system",
                ENGLISH_REPAIR_SYSTEM,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=failed_ids,
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"English repair alignment failure: {reason}"
        )

    text_failures = validate_english_text(
        result.items
    )

    if text_failures:
        raise ValueError(
            "English repair still failed basic validation: "
            f"{text_failures}"
        )

    repair_map = {
        item.record_id: item
        for item in result.items
    }

    merged = [
        repair_map.get(
            item.record_id,
            item,
        )
        for item in state["english_items"]
    ]

    return {
        "english_items": merged,
        "english_failed_ids": [],
        "english_retry_count": retry_count + 1,
    }


# ============================================================================
# Node 6/7: Translation
# ============================================================================

async def translate_chinese(
    state: WorkflowState,
) -> WorkflowState:
    english_map = map_by_id(
        state["english_items"]
    )

    source_items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
        }
        for record_id in state["target_ids"]
    ]

    prompt = f"""
Translate every source item into Simplified Chinese.

Source items:
{source_items}

Return exactly one translation for every record_id.
"""

    result = await translator.ainvoke(
        [
            (
                "system",
                TRANSLATOR_SYSTEM
                + "\nTarget language: Simplified Chinese.",
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=state["target_ids"],
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"Chinese structured-output alignment failure: {reason}"
        )

    failures = validate_translation_text(
        result.items
    )

    return {
        "chinese_items": result.items,
        "chinese_failed_ids": sorted(
            failures.keys()
        ),
        "errors": [
                f"Chinese translation validation: "
                f"{record_id}: {reason}"
                for record_id, reason
                in failures.items()
            ]
        ,
    }


async def translate_indonesian(
    state: WorkflowState,
) -> WorkflowState:
    english_map = map_by_id(
        state["english_items"]
    )

    source_items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
        }
        for record_id in state["target_ids"]
    ]

    prompt = f"""
Translate every source item into standard Bahasa Indonesia.

Source items:
{source_items}

Return exactly one translation for every record_id.

Additional requirements:
- Use standard Bahasa Indonesia.
- Do not use Malaysian Malay.
- Preserve all semantic information from English.
"""

    result = await translator.ainvoke(
        [
            (
                "system",
                TRANSLATOR_SYSTEM
                + "\nTarget language: Standard Bahasa Indonesia.",
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=state["target_ids"],
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"Indonesian structured-output alignment failure: {reason}"
        )

    failures = validate_translation_text(
        result.items
    )

    return {
        "indonesian_items": result.items,
        "indonesian_failed_ids": sorted(
            failures.keys()
        ),
        "errors": [
                f"Indonesian translation validation: "
                f"{record_id}: {reason}"
                for record_id, reason
                in failures.items()
            ],
    }


# ============================================================================
# Translation Basic-Validation Nodes
# ============================================================================

async def validate_chinese(
    state: WorkflowState,
) -> WorkflowState:
    expected_ids = state["target_ids"]
    actual_ids = [
        item.record_id
        for item in state["chinese_items"]
    ]

    failures: dict[str, str] = {}

    ok, reason = validate_ids(
        expected_ids=expected_ids,
        actual_ids=actual_ids,
    )

    if not ok:
        for record_id in expected_ids:
            failures[record_id] = reason

    failures.update(
        validate_translation_text(
            state["chinese_items"]
        )
    )

    chinese_failed_ids = sorted(failures.keys())

    return {
        "chinese_failed_ids": chinese_failed_ids,
        "cn_valid_status": ValidStatus.SUCCESS if len(chinese_failed_ids) == 0 else ValidStatus.FAIL,
        "errors": [
                f"Chinese validation: "
                f"{record_id}: {reason}"
                for record_id, reason
                in failures.items()
            ]
        ,
    }


async def validate_indonesian(
    state: WorkflowState,
) -> WorkflowState:
    expected_ids = state["target_ids"]
    actual_ids = [
        item.record_id
        for item in state["indonesian_items"]
    ]

    failures: dict[str, str] = {}

    ok, reason = validate_ids(
        expected_ids=expected_ids,
        actual_ids=actual_ids,
    )

    if not ok:
        for record_id in expected_ids:
            failures[record_id] = reason

    failures.update(
        validate_translation_text(
            state["indonesian_items"]
        )
    )

    indonesian_failed_ids = sorted(failures.keys())

    return {
        "indonesian_failed_ids": indonesian_failed_ids,
        "id_valid_status": ValidStatus.SUCCESS if len(indonesian_failed_ids) == 0 else ValidStatus.FAIL,
        "errors": [
                f"Indonesian validation: "
                f"{record_id}: {reason}"
                for record_id, reason
                in failures.items()
            ]
        ,
    }


# ============================================================================
# Translation Repair Nodes
# ============================================================================

async def repair_chinese(
    state: WorkflowState,
) -> WorkflowState:
    failed_ids = state["chinese_failed_ids"]

    if not failed_ids:
        return {}

    retry_count = state.get(
        "chinese_retry_count",
        0,
    )

    if retry_count >= MAX_TRANSLATION_RETRIES:
        raise RuntimeError(
            "Maximum Chinese translation retries exceeded for: "
            f"{failed_ids}"
        )

    english_map = map_by_id(
        state["english_items"]
    )

    chinese_map = map_by_id(
        state["chinese_items"]
    )

    items = []

    for record_id in failed_ids:
        items.append(
            {
                "record_id": record_id,
                "english": english_map[record_id].english,
                "previous_translation": (
                    chinese_map[record_id].text
                    if record_id in chinese_map
                    else ""
                ),
            }
        )

    prompt = f"""
Repair these Simplified Chinese translations.

Items:
{items}

Return exactly one repaired translation for every record_id.
"""

    result = await translation_repair.ainvoke(
        [
            (
                "system",
                TRANSLATION_REPAIR_SYSTEM
                + "\nTarget language: Simplified Chinese.",
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=failed_ids,
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"Chinese repair alignment failure: {reason}"
        )

    text_failures = validate_translation_text(
        result.items
    )

    if text_failures:
        raise ValueError(
            "Chinese translation repair failed basic validation: "
            f"{text_failures}"
        )

    repair_map = {
        item.record_id: item
        for item in result.items
    }

    merged = [
        repair_map.get(
            item.record_id,
            item,
        )
        for item in state["chinese_items"]
    ]

    return {
        "chinese_items": merged,
        "chinese_failed_ids": [],
        "chinese_retry_count": retry_count + 1,
    }


async def repair_indonesian(
    state: WorkflowState,
) -> WorkflowState:
    failed_ids = state["indonesian_failed_ids"]

    if not failed_ids:
        return {}

    retry_count = state.get(
        "indonesian_retry_count",
        0,
    )

    if retry_count >= MAX_TRANSLATION_RETRIES:
        raise RuntimeError(
            "Maximum Indonesian translation retries exceeded for: "
            f"{failed_ids}"
        )

    english_map = map_by_id(
        state["english_items"]
    )

    indonesian_map = map_by_id(
        state["indonesian_items"]
    )

    items = []

    for record_id in failed_ids:
        items.append(
            {
                "record_id": record_id,
                "english": english_map[record_id].english,
                "previous_translation": (
                    indonesian_map[record_id].text
                    if record_id in indonesian_map
                    else ""
                ),
            }
        )

    prompt = f"""
Repair these Indonesian translations.

Items:
{items}

Requirements:
- Use standard Bahasa Indonesia.
- Do not use Malaysian Malay.
- Preserve the English meaning exactly.
- Return exactly one repaired translation for every record_id.
"""

    result = await translation_repair.ainvoke(
        [
            (
                "system",
                TRANSLATION_REPAIR_SYSTEM
                + "\nTarget language: Standard Bahasa Indonesia.",
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=failed_ids,
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"Indonesian repair alignment failure: {reason}"
        )

    text_failures = validate_translation_text(
        result.items
    )

    if text_failures:
        raise ValueError(
            "Indonesian translation repair failed basic validation: "
            f"{text_failures}"
        )

    repair_map = {
        item.record_id: item
        for item in result.items
    }

    merged = [
        repair_map.get(
            item.record_id,
            item,
        )
        for item in state["indonesian_items"]
    ]

    return {
        "indonesian_items": merged,
        "indonesian_failed_ids": [],
        "indonesian_retry_count": retry_count + 1,
    }


# ============================================================================
# Deterministic Alignment / Join
# ============================================================================

async def merge_by_id(
    state: WorkflowState,
) -> WorkflowState:
    """
    The critical anti-misalignment step.

    No LLM is involved.

    The three language datasets are joined exclusively by the internal
    immutable record_id.

    Final public keys are:
        EN = English
        CN = Chinese
        ID = Indonesian
    """

    target_ids = state["target_ids"]

    english_map = map_by_id(
        state["english_items"]
    )
    chinese_map = map_by_id(
        state["chinese_items"]
    )
    indonesian_map = map_by_id(
        state["indonesian_items"]
    )

    if set(english_map) != set(target_ids):
        raise ValueError(
            "English IDs do not exactly match target IDs."
        )

    if set(chinese_map) != set(target_ids):
        raise ValueError(
            "Chinese IDs do not exactly match target IDs."
        )

    if set(indonesian_map) != set(target_ids):
        raise ValueError(
            "Indonesian IDs do not exactly match target IDs."
        )

    final_items = []

    for record_id in target_ids:
        final_items.append(
            {
                "EN": english_map[record_id].english,
                "CN": chinese_map[record_id].text,
                "ID": indonesian_map[record_id].text,
            }
        )

    return {
        "final_items": final_items,
    }


# ============================================================================
# Semantic Translation QA
# ============================================================================

async def semantic_alignment_qa(
    state: WorkflowState,
) -> WorkflowState:
    target_ids = state["target_ids"]

    english_map = map_by_id(
        state["english_items"]
    )
    chinese_map = map_by_id(
        state["chinese_items"]
    )
    indonesian_map = map_by_id(
        state["indonesian_items"]
    )

    qa_items = [
        {
            "record_id": record_id,
            "english": english_map[record_id].english,
            "chinese": chinese_map[record_id].text,
            "indonesian": indonesian_map[record_id].text,
        }
        for record_id in target_ids
    ]

    prompt = f"""
Evaluate every multilingual record below.

Records:
{qa_items}

Return exactly one QA result for every record_id.
"""

    result = await alignment_qa.ainvoke(
        [
            (
                "system",
                ALIGNMENT_QA_SYSTEM,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    ok, reason = validate_ids(
        expected_ids=target_ids,
        actual_ids=[
            item.record_id
            for item in result.items
        ],
    )

    if not ok:
        raise ValueError(
            f"Semantic QA alignment failure: {reason}"
        )

    chinese_failed = [
        item.record_id
        for item in result.items
        if not item.chinese_ok
    ]

    indonesian_failed = [
        item.record_id
        for item in result.items
        if not item.indonesian_ok
    ]

    qa_errors = [
        f"{item.record_id}: {item.reason}"
        for item in result.items
        if not item.chinese_ok
        or not item.indonesian_ok
    ]

    return {
        "chinese_failed_ids": chinese_failed,
        "indonesian_failed_ids": indonesian_failed,
        "errors": qa_errors,
    }


# ============================================================================
# Semantic QA Routing
# ============================================================================

def route_after_semantic_qa(
    state: WorkflowState,
) -> Literal[
    "repair_chinese",
    "repair_indonesian",
    "final_validation",
]:
    if state.get("chinese_failed_ids"):
        return "repair_chinese"

    if state.get("indonesian_failed_ids"):
        return "repair_indonesian"

    return "final_validation"


# ============================================================================
# Final Validation
# ============================================================================

async def final_validation(
    state: WorkflowState,
) -> WorkflowState:
    final_items = state["final_items"]
    target_count = state["target_count"]

    # Deterministic validation first.
    if len(final_items) != target_count:
        raise ValueError(
            f"Final count mismatch: expected {target_count}, "
            f"got {len(final_items)}."
        )

    if any(
        not item.get("EN", "").strip()
        or not item.get("CN", "").strip()
        or not item.get("ID", "").strip()
        for item in final_items
    ):
        raise ValueError(
            "Final dataset contains an empty EN/CN/ID field."
        )

    english_values = [
        normalize_text(item["EN"])
        for item in final_items
    ]

    if len(set(english_values)) != target_count:
        raise ValueError(
            "Final dataset contains duplicate English sentences."
        )

    prompt = f"""
Requested count:
{target_count}

Final dataset:
{final_items}

Validate the final dataset.
"""

    result = await final_qa.ainvoke(
        [
            (
                "system",
                FINAL_QA_SYSTEM,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    if not result.valid:
        raise ValueError(
            f"Final LLM validation failed: {result.reason}"
        )

    return {}


# ============================================================================
# Graph Routing
# ============================================================================

def route_after_english_validation(
    state: WorkflowState,
) -> Literal[
    "repair_english",
    "generate_next_english_batch",
    "translate",
]:
    if state.get("english_failed_ids"):
        return "repair_english"

    generated_count = len(
        state["english_items"]
    )

    target_count = state["target_count"]

    if generated_count < target_count:
        return "generate_next_english_batch"

    return "translate"

# region ============== Graph Construction =================================

def build_graph():
    graph = StateGraph(WorkflowState)

    # English generation
    graph.add_node("initialize_request", initialize_request)
    graph.add_node("plan_diversity", plan_diversity)
    graph.add_node("generate_english", generate_english)
    graph.add_node("validate_english",validate_english)
    graph.add_node("repair_english", repair_english)

    # Translation
    graph.add_node("start_translation", lambda state: {})

    graph.add_node("translate_chinese", translate_chinese)
    graph.add_node("validate_chinese", validate_chinese)
    graph.add_node("repair_chinese", repair_chinese)

    graph.add_node("translate_indonesian", translate_indonesian)
    graph.add_node("validate_indonesian", validate_indonesian)
    graph.add_node("repair_indonesian", repair_indonesian)

    # Merge / QA
    graph.add_node("merge_by_id", merge_by_id)
    graph.add_node("semantic_alignment_qa", semantic_alignment_qa)
    graph.add_node("final_validation", final_validation)

    # ------------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------------
    graph.add_edge(START, "initialize_request")
    graph.add_edge("initialize_request", "plan_diversity")
    graph.add_edge("plan_diversity", "generate_english")

    # ------------------------------------------------------------------------
    # English generation loop
    # ------------------------------------------------------------------------
    graph.add_edge("generate_english", "validate_english")
    graph.add_edge("repair_english", "validate_english")
    graph.add_conditional_edges(
        "validate_english",
        lambda s: s["valid_status"],
        {
            ValidStatus.FAIL: "repair_english",
            ValidStatus.PENDING_BATCH: "generate_english",
            ValidStatus.SUCCESS: "start_translation",
        },
    )

    # ------------------------------------------------------------------------
    # Parallel translation:
    #   One validated English source set fans out into different independent
    #   translation branches.
    # ------------------------------------------------------------------------

    # Chinese translation
    graph.add_edge("start_translation", "translate_chinese")
    graph.add_edge("translate_chinese", "validate_chinese")
    graph.add_edge("repair_chinese", "validate_chinese")
    graph.add_conditional_edges(
        "validate_chinese",
        lambda s: s["cn_valid_status"],
        {
            ValidStatus.FAIL: "repair_chinese",
            ValidStatus.SUCCESS: "merge_by_id",
        },
    )

    # Indonesian translation
    graph.add_edge("start_translation", "translate_indonesian")
    graph.add_edge("translate_indonesian", "validate_indonesian")
    graph.add_edge("repair_indonesian", "validate_indonesian")
    graph.add_conditional_edges(
            "validate_indonesian",
            lambda s: s["id_valid_status"],
            {
                ValidStatus.FAIL: "repair_indonesian",
                ValidStatus.SUCCESS: "merge_by_id",
            },
        )

    # ------------------------------------------------------------------------
    # Meges the two branches back to a single branch: ID alignment
    # ------------------------------------------------------------------------
    # Any repaired translation is semantically re-evaluated.
    graph.add_edge("merge_by_id", "semantic_alignment_qa")
    graph.add_conditional_edges(
        "semantic_alignment_qa",
        route_after_semantic_qa,
        {
            "repair_chinese": "repair_chinese",
            "repair_indonesian": "repair_indonesian",
            "final_validation": "final_validation",
        },
    )

    graph.add_edge("final_validation", END)

    return graph.compile()

app = build_graph()

# endregion ============== Graph Construction =================================

# region ============== Workflow Public API =================================

async def generate_multilingual_sentences(
    topic: str,
    count: int,
    difficulty: str = "B1",
    batch_size: int = DEFAULT_BATCH_SIZE,
    existing_english_sentences: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Generate exactly `count` multilingual records.

    Parameters
    ----------
    topic:
        Generation topic.

    count:
        Exact number of final records required.

    difficulty:
        Learner level, for example A1/A2/B1/B2/C1.

    batch_size:
        English generation batch size.

    existing_english_sentences:
        Optional previous English sentences from your database / ChromaDB /
        pgvector / other memory system.

        These are used for diversity and semantic duplicate rejection.

    Returns
    -------
    list[dict[str, str]]

    Example:
        [
            {
                "EN": "I forgot my passport.",
                "CN": "我忘记带护照了。",
                "ID": "Saya lupa membawa paspor saya."
            },
            {
                "EN": "Could you call a taxi for me?",
                "CN": "你能帮我叫一辆出租车吗？",
                "ID": "Bisakah Anda memanggilkan taksi untuk saya?"
            }
        ]
    """

    if count <= 0:
        raise ValueError(
            "count must be greater than zero."
        )

    if batch_size <= 0:
        raise ValueError(
            "batch_size must be greater than zero."
        )

    initial_state: WorkflowState = {
        "topic": topic,
        "difficulty": difficulty,
        "target_count": count,
        "batch_size": batch_size,
        "existing_english_sentences": (
            existing_english_sentences or []
        ),
    }

    final_state = await app.ainvoke(initial_state,
        config={
            "recursion_limit": 200,
        },
    )

    return final_state["final_items"]

def generate_multilingual_sentences_sync(
    topic: str,
    count: int,
    difficulty: str = "B1",
    batch_size: int = DEFAULT_BATCH_SIZE,
    existing_english_sentences: list[str] | None = None,
) -> list[dict[str, str]]:
    return asyncio.run(
        generate_multilingual_sentences(
            topic=topic,
            count=count,
            difficulty=difficulty,
            batch_size=batch_size,
            existing_english_sentences=existing_english_sentences,
        )
    )

# endregion ============== Workflow Public API =================================

# ========================== Example ======================================
if __name__ == "__main__":
    result = generate_multilingual_sentences_sync(
        topic="Travel and everyday situations",
        count=10,
        difficulty="A1",
        batch_size=5,
        existing_english_sentences=[],
    )

    import json

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

