from typing import TypedDict

from app.utils.types import LANG_OPTIONS, CEFRLevel, Language

class Cache(TypedDict):
    cur_lesson: int
    cur_sort_by: str
    # gen lesson dialog input cache
    source_language: Language
    source_max_len: int
    topic: str
    difficulty: CEFRLevel
    target_count: int
    display_language_1: LANG_OPTIONS
    display_language_2: LANG_OPTIONS
    batch_size: int
    max_concurrency: int