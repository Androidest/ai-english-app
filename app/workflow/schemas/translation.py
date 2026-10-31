from pydantic import BaseModel, ConfigDict, Field


class TranslationItem(BaseModel):
    """One translated sentence, keyed by the immutable record_id."""

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TranslationBatch(BaseModel):
    """A batch of translated sentences."""

    model_config = ConfigDict(extra="forbid")

    items: list[TranslationItem] = Field(min_length=1)
