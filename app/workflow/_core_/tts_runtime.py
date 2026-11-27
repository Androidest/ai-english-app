from pathlib import Path
import base64

from app.workflow._core_.tts_config import TTSConfig
from app.workflow._core_.tts_providers.provider_base import TTSProvider
from app.workflow._core_.tts_providers.openai import OpenAITTSProvider
from app.workflow._core_.tts_providers.deepseek import DeepSeekTTSProvider
from app.utils.types import TTSProviderType

PROVIDER_REGISTRY: dict[TTSProviderType, type[TTSProvider]] = {
    "openai": OpenAITTSProvider,
    "deepseek": DeepSeekTTSProvider,
}

class TTSRuntime:

    def __init__(self, config: TTSConfig):
        provider_name = config.model_provider
        if provider_name not in PROVIDER_REGISTRY:
            raise ValueError(
                f"Unsupported TTS provider: {provider_name}. "
                f"Available: {list(PROVIDER_REGISTRY)}"
            )

        self.model = PROVIDER_REGISTRY[provider_name](config)

    def get_model(self) -> TTSProvider:
        return self.model

    def save_audio(
        self, 
        data: bytes,
        path: Path,
    ):
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def to_base64(
        self,
        data: bytes,
    ) -> str:
        return base64.b64encode(data).decode("ascii")
