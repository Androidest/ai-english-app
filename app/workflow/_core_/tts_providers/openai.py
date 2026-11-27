# app/workflow/_core_/tts_runtime.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
import httpx

from app.workflow._core_.tts_providers.provider_base import TTSProvider
from app.workflow._core_.tts_config import TTSConfig

VOICE = Literal["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]
FORMAT = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] 

class OpenAITTSConfig(TTSConfig):
    base_url: str = Field(default="https://api.openai.com/v1/audio/speech", description="Full URL")
    voice_id: VOICE = Field(default=VOICE.__args__[0], description="Voice ID")
    model: str = Field(default="gpt-4o-mini-tts", description="Model")
    
class OpenAITTSProvider(TTSProvider):
    config_type = OpenAITTSConfig

    def synthesize(
        self,
        text: str,
        *,
        voice_id: VOICE = None,
        audio_format: FORMAT = "wav",
        **kwargs: Any,
    ) -> bytes:
        payload = {
            "input": text,
            "model": self._config.model,
            "voice": voice_id or self._config.voice_id,
            "response_format": audio_format,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(self._config.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content