from pydantic import Field

from app.workflow._core_.llm_config import LLMConfig

class TTSConfig(LLMConfig):
    voice_id: str = Field(default="")


