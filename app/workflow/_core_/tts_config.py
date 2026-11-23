from pydantic import Field

from app.utils.types import TTSProviderType
from app.workflow._core_.llm_config import LLMConfig

class TTSConfig(LLMConfig):
    model_provider: TTSProviderType = Field(default=TTSProviderType.__args__[0], description="Provider")
    voice_id: str = Field(default="", description="Voice ID")

    def validate_to_error(self):
        super().validate_to_error()

        if self.voice_id == "":
            self.error = "voice_id is required"


