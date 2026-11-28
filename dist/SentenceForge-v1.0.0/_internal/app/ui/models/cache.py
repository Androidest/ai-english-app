from pydantic import BaseModel, Field
from typing import TypedDict

from app.ui.models.lesson_gen_params import LessonGenParams
from app.utils.types import SORTING_OPTIONS

class Cache(BaseModel):
    cur_lesson: str = Field(default="")
    cur_sort_by: SORTING_OPTIONS = Field(default='latest')
    
    gen_params: LessonGenParams = Field(default_factory=LessonGenParams)

class CacheUpdate(TypedDict, total=False):
    cur_lesson: str
    cur_sort_by: SORTING_OPTIONS

    gen_params: LessonGenParams  

assert set(CacheUpdate.__annotations__) == set(Cache.model_fields)