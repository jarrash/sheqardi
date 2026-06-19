"""Third engine — modular extension point.

In this MVP the third engine is a *safe placeholder*: when it is not configured
(the default) it returns a failed/"skipped" :class:`EngineResult` without ever
raising, so it can never break a request. It exists so a real third backend can
be dropped in later by implementing :meth:`_transcribe`.

Suggested concrete backends to wire up here:

* **NVIDIA Parakeet** (NeMo) — high-accuracy ASR.
* A **HuggingFace Arabic** model (e.g. ``transformers`` ``pipeline("automatic-speech-recognition", ...)``).
* Any external **STT API** (Google, Azure, AWS Transcribe, ...).

To enable, set ``THIRD_ENGINE_ENABLED=true`` and implement ``_transcribe``.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.engines.base import BaseEngine, EngineResult

logger = logging.getLogger(__name__)


class ThirdEngine(BaseEngine):
    """Placeholder engine; replace ``_transcribe`` with a real backend."""

    name = "third-engine"

    def __init__(self, enabled: bool | None = None) -> None:
        self.enabled = settings.third_engine_enabled if enabled is None else enabled

    def version(self) -> str:
        return f"{self.name} (placeholder)"

    def run(self, audio_path: str, language: str) -> EngineResult:  # type: ignore[override]
        """Skip cleanly when disabled; otherwise defer to the base fail-soft wrapper."""
        if not self.enabled:
            logger.info("Third engine is disabled; skipping.")
            return EngineResult(
                engine_name=self.name,
                language=language,
                text="",
                processing_time_seconds=0.0,
                success=False,
                error="third engine not configured",
                version=self.version(),
            )
        return super().run(audio_path, language)

    def _transcribe(self, audio_path: str, language: str) -> str:
        # TODO: integrate a real STT backend (NVIDIA Parakeet / HuggingFace / API).
        raise NotImplementedError("Third engine backend is not implemented yet.")
