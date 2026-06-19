"""Base engine contract.

Every speech-to-text engine implements :class:`BaseEngine`. The public entry
point is :meth:`BaseEngine.run`, which wraps the concrete ``_transcribe``
implementation with timing and *fail-soft* error handling: a failing engine
returns a failed :class:`EngineResult` instead of raising, so one broken engine
never aborts a request that other engines can still satisfy.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EngineResult:
    """Outcome of a single engine transcribing a single audio file."""

    engine_name: str
    language: str
    text: str
    processing_time_seconds: float
    success: bool = True
    error: Optional[str] = None
    version: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "engine_name": self.engine_name,
            "language": self.language,
            "text": self.text,
            "processing_time_seconds": round(self.processing_time_seconds, 3),
            "success": self.success,
            "error": self.error,
            "version": self.version,
        }


class BaseEngine(ABC):
    """Abstract speech-to-text engine."""

    #: Stable, human-readable engine identifier (e.g. ``"faster-whisper-large-v3"``).
    name: str = "base-engine"

    def version(self) -> str:
        """Return a version string for the engine. Override when richer info is available."""
        return self.name

    @abstractmethod
    def _transcribe(self, audio_path: str, language: str) -> str:
        """Transcribe ``audio_path`` and return the recognised text.

        Implementations may raise; :meth:`run` converts exceptions into a failed
        :class:`EngineResult`.
        """

    def run(self, audio_path: str, language: str) -> EngineResult:
        """Execute the engine, capturing timing and any failure."""
        start = time.perf_counter()
        try:
            text = self._transcribe(audio_path, language)
            elapsed = time.perf_counter() - start
            logger.info("Engine %s finished in %.2fs", self.name, elapsed)
            return EngineResult(
                engine_name=self.name,
                language=language,
                text=text.strip(),
                processing_time_seconds=elapsed,
                success=True,
                version=self.version(),
            )
        except Exception as exc:  # noqa: BLE001 - fail-soft by design
            elapsed = time.perf_counter() - start
            logger.warning("Engine %s failed after %.2fs: %s", self.name, elapsed, exc)
            return EngineResult(
                engine_name=self.name,
                language=language,
                text="",
                processing_time_seconds=elapsed,
                success=False,
                error=str(exc),
                version=self.version(),
            )
