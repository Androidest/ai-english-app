from pydantic import BaseModel, ConfigDict, Field


class EnglishSentence(BaseModel):
    """One canonical English source sentence."""

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    english: str = Field(min_length=1)


class EnglishBatch(BaseModel):
    """A batch of canonical English source sentences."""

    model_config = ConfigDict(extra="forbid")

    items: list[EnglishSentence] = Field(min_length=1)
