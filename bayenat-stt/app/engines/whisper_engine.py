"""OpenAI Whisper (open-source) engine.

As with the faster-whisper engine, ``whisper`` and ``torch`` are imported lazily
so a missing dependency degrades into a recorded engine error rather than a
start-up crash.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.engines.base import BaseEngine

logger = logging.getLogger(__name__)


class WhisperEngine(BaseEngine):
    """Transcription via the reference OpenAI Whisper implementation."""

    def __init__(self, model_size: str | None = None, device: str | None = None) -> None:
        self.model_size = model_size or settings.whisper_model
        self.device_pref = device or settings.device
        self.name = f"whisper-{self.model_size}"
        self._model = None

    def version(self) -> str:
        try:
            import whisper  # type: ignore

            return f"openai-whisper {getattr(whisper, '__version__', '?')} / {self.model_size}"
        except Exception:  # noqa: BLE001
            return self.name

    def _resolve_device(self) -> str:
        device = self.device_pref
        if device == "auto":
            try:
                import torch  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:  # noqa: BLE001
                device = "cpu"
        return device

    def _load_model(self):
        if self._model is None:
            import whisper  # type: ignore

            device = self._resolve_device()
            logger.info("Loading whisper model=%s device=%s", self.model_size, device)
            self._model = whisper.load_model(self.model_size, device=device)
        return self._model

    def _transcribe(self, audio_path: str, language: str) -> str:
        model = self._load_model()
        result = model.transcribe(audio_path, language=language)
        return str(result.get("text", "")).strip()
