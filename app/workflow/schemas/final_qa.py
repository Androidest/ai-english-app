from pydantic import BaseModel, ConfigDict, Field


class FinalQA(BaseModel):
    """Final validation verdict of the multilingual dataset."""

    valid: bool
    reason: str = Field(min_length=1)
