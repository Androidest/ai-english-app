from pydantic import BaseModel, ConfigDict, Field


class EnglishSentence(BaseModel):
    """One canonical English source sentence."""

    record_id: str = Field(min_length=1)
    english: str = Field(min_length=1)


class EnglishBatch(BaseModel):
    """A batch of canonical English source sentences."""

    items: list[EnglishSentence] = Field(min_length=1)
