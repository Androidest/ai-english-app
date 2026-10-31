from pydantic import BaseModel, ConfigDict, Field


class FinalQA(BaseModel):
    """Final validation verdict of the multilingual dataset."""

    model_config = ConfigDict(extra="forbid")

    valid: bool
    reason: str = Field(min_length=1)
