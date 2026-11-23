from typing import TypedDict, NotRequired
import json
from pydantic import BaseModel, Field

from app.utils.paths import PATH_LLM
from app.utils.types import ProviderType

class LLMConfig(BaseModel):
    alias: str = Field(default="")
    model_provider: ProviderType = Field(default=ProviderType.__args__[0])
    model: str = Field(default="")
    base_url: str = Field(default="")
    api_key: str = Field(default="")

    editing: bool = Field(default=False, exclude=True)
    error: str = Field(default="", exclude=True)
    id: str = Field(default="", exclude=True)
    is_new: bool = Field(default=False, exclude=True)


