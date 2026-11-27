# app/workflow/_core_/tts_runtime.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
import httpx

from app.workflow._core_.tts_providers.provider_base import TTSProvider
from app.workflow._core_.tts_config import TTSConfig

VOICE = Literal["stella", "tide"]
FORMAT = Literal["wav", "pcm"]

class DeepSeekTTSConfig(TTSConfig):
    base_url: str = Field(default="https://api.deepseek.com/v1/tools/tts", description="Full URL")
    voice_id: VOICE = Field(default=VOICE.__args__[0], description="Voice ID")

    model: str = Field(default="-- Not required --", description="Model", deprecated=True)

class DeepSeekTTSProvider(TTSProvider):
    config_type = DeepSeekTTSConfig

    def synthesize(
        self,
        text: str,
        *,
        voice_id: VOICE = None,
        audio_format: FORMAT = "wav",
        filter_markdown: bool = False,
        **kwargs: Any,
    ) -> bytes:
        payload = {
            "text": text,
            "voice_id": voice_id or self._config.voice_id,
            "format": audio_format,
            "filter_markdown": filter_markdown,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=120.0) as client:
            with client.stream("POST", self._config.base_url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                return b"".join(resp.iter_bytes())