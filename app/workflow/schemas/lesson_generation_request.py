from pydantic import BaseModel, Field

from app.workflow.nodes._common import DEFAULT_BATCH_SIZE


class LessonGenerationRequest(BaseModel):
    """Public input of the multilingual lesson generation workflow."""
    
    topic: str
    count: int
    difficulty: str = "B1"
    batch_size: int = DEFAULT_BATCH_SIZE
    existing_english_sentences: list[str] = Field(default_factory=list)
