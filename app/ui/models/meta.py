from typing import TypedDict

from app.utils.types import CEFRLevel, Language

class Meta(TypedDict):
    name: str
    time_created: float
    progress_idx: int
    phrases_flag: dict[str, int] # key: page index, val: stores flags as bits. 
    correct_count: int
    favourite_count: int
    total: int

    source_language: Language
    source_max_len: int
    topic: str
    difficulty: CEFRLevel
    target_count: int
    display_languages: list[CEFRLevel]
    batch_size: int
    max_concurrency: int