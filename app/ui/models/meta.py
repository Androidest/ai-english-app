from pydantic import BaseModel, Field
from typing import TypedDict

from app.ui.models.lesson_gen_params import LessonGenParams

class Meta(BaseModel):
    name: str = Field(default="")
    time_created: float = Field(default=0) 
    progress_idx: int = Field(default=0)
    phrases_flag: dict[str, int] = Field(default_factory=dict)# key: page index, val: stores flags as bits. 
    correct_count: int = Field(default=0)
    favourite_count: int = Field(default=0)
    total: int = Field(default=0)
    ai_model_name: str = Field(default="Unknown")

    gen_params: LessonGenParams = Field(default_factory=LessonGenParams)

class MetaUpdate(TypedDict, total=False):
    name: str
    time_created: float
    progress_idx: int
    phrases_flag: dict[str, int]
    correct_count: int
    favourite_count: int
    total: int
    ai_model_name: str

    gen_params: LessonGenParams

assert set(MetaUpdate.__annotations__) == set(Meta.model_fields)