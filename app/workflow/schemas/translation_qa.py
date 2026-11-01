from pydantic import BaseModel, ConfigDict, Field


class TranslationQAItem(BaseModel):
    """Semantic QA verdict of one multilingual record."""
    
    record_id: str = Field(min_length=1)
    chinese_ok: bool
    indonesian_ok: bool
    reason: str = Field(min_length=1)


class TranslationQABatch(BaseModel):
    """Semantic QA verdicts of the whole multilingual dataset."""
    
    items: list[TranslationQAItem] = Field(min_length=1)
