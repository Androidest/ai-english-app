from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

class AIConfig(BaseModel, ABC):
    editing: bool = Field(default=False, exclude=True)
    error: str = Field(default="", exclude=True)
    id: str = Field(default="", exclude=True)
    is_new: bool = Field(default=False, exclude=True)

    @abstractmethod
    def validate_to_error(self):
        raise NotImplementedError("validate_to_error not implemented!")
        