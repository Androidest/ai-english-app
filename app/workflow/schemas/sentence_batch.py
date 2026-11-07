from pydantic import BaseModel, ConfigDict, Field

class Sentence(BaseModel):
    """A sentence item."""
    
    uid: str = Field(min_length=1, description="An immutable unique ID/key for each sentence")
    val: str = Field(min_length=1, description="Stores one sentence.")


class SentenceBatch(BaseModel):
    """A batch of canonical sentences."""

    items: list[Sentence]
