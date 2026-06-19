"""Faster-Whisper engine (CTranslate2 backend).

Heavy dependencies (``faster_whisper``, ``torch``) are imported lazily inside
``_transcribe`` so the API can start — and the test-suite can run — even when
they are not installed. Any import or model-load failure is surfaced through the
fail-soft wrapper in :class:`~app.engines.base.BaseEngine`.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.engines.base import BaseEngine

logger = logging.getLogger(__name__)


class FasterWhisperEngine(BaseEngine):
    """Transcription via the faster-whisper (CTranslate2) implementation of Whisper."""

    def __init__(self, model_size: str | None = None, device: str | None = None) -> None:
        self.model_size = model_size or settings.faster_whisper_model
        self.device_pref = device or settings.device
        self.name = f"faster-whisper-{self.model_size}"
        self._model = None  # lazily instantiated, then cached

    def version(self) -> str:
        try:
            import faster_whisper  # type: ignore

            return f"faster-whisper {getattr(faster_whisper, '__version__', '?')} / {self.model_size}"
        except Exception:  # noqa: BLE001
            return self.name

    def _resolve_device(self) -> tuple[str, str]:
        """Return ``(device, compute_type)`` based on configuration and CUDA availability."""
        device = self.device_pref
        if device == "auto":
            try:
                import torch  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:  # noqa: BLE001
                device = "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        return device, compute_type

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore

            device, compute_type = self._resolve_device()
            logger.info(
                "Loading faster-whisper model=%s device=%s compute_type=%s",
                self.model_size,
                device,
                compute_type,
            )
            self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        return self._model

    def _transcribe(self, audio_path: str, language: str) -> str:
        model = self._load_model()
        segments, _info = model.transcribe(audio_path, language=language)
        return " ".join(segment.text.strip() for segment in segments).strip()
