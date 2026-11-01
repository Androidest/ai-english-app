from pydantic import BaseModel, ConfigDict, Field


class TranslationItem(BaseModel):
    """One translated sentence, keyed by the immutable record_id."""

    record_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TranslationBatch(BaseModel):
    """A batch of translated sentences."""

    items: list[TranslationItem] = Field(min_length=1)
