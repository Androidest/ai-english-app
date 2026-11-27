# app/workflow/_core_/tts_runtime.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from app.workflow._core_.tts_config import TTSConfig

class TTSProvider(ABC):
    """Protocol for a single TTS provider."""

    config_type = TTSConfig

    def __init__(self, config: TTSConfig):
        self._config = config

    @abstractmethod
    def synthesize(
        self,
        text: str,
        **kwargs: Any,
    ) -> bytes:
        """Return raw audio bytes."""
        ...