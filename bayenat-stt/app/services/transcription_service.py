"""Orchestrate the full transcription pipeline.

Runs every configured engine over the audio file (fail-soft), compares their
output, fingerprints the final text, writes the chain-of-custody report and
persists a database record. Engine calls are blocking/CPU-bound, so they run in
a worker thread to keep the event loop responsive.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.engines.base import BaseEngine, EngineResult
from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.engines.third_engine import ThirdEngine
from app.engines.whisper_engine import WhisperEngine
from app.models import database
from app.services import comparison_service, hash_service, report_service

logger = logging.getLogger(__name__)


def default_engines() -> List[BaseEngine]:
    """The three engines used by the MVP, in display order."""
    return [FasterWhisperEngine(), WhisperEngine(), ThirdEngine()]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def transcribe_audio(
    *,
    audio_path: str,
    original_filename: str,
    uploaded_at: str,
    language: str,
    case_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
    engines: Optional[List[BaseEngine]] = None,
) -> dict:
    """Execute the pipeline and return a dict matching ``TranscribeResponse``.

    Raises :class:`ValueError` when no engine yields a usable transcript.
    """
    engines = engines or default_engines()
    processing_started_at = _now_iso()

    # Hash the audio (chain of custody) — run off the event loop.
    audio_hash = await asyncio.to_thread(hash_service.sha256_file, audio_path)

    # Run engines concurrently in worker threads (each is internally blocking).
    results: List[EngineResult] = await asyncio.gather(
        *(asyncio.to_thread(engine.run, audio_path, language) for engine in engines)
    )

    for r in results:
        if not r.success:
            logger.warning("Engine %s reported error: %s", r.engine_name, r.error)

    # Compare and select the final transcript (raises if none succeeded).
    comparison = comparison_service.compare(results)

    final_text_hash = hash_service.sha256_text(comparison.final_transcript)
    processing_finished_at = _now_iso()

    report = report_service.build_report(
        original_filename=original_filename,
        uploaded_at=uploaded_at,
        processing_started_at=processing_started_at,
        processing_finished_at=processing_finished_at,
        audio_hash=audio_hash,
        final_text_hash=final_text_hash,
        engine_results=results,
        comparison=comparison,
        case_id=case_id,
        evidence_id=evidence_id,
    )
    report_path = report_service.save_report(report)

    # Persist a lightweight record for later lookup.
    try:
        database.insert_record(
            case_id=case_id,
            evidence_id=evidence_id,
            original_filename=original_filename,
            audio_path=audio_path,
            report_path=report_path,
            audio_hash=audio_hash,
            final_text_hash=final_text_hash,
            confidence_score=comparison.confidence_score,
        )
    except Exception as exc:  # noqa: BLE001 - DB failure shouldn't lose the result
        logger.error("Failed to persist transcription record: %s", exc)

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "audio_hash": audio_hash,
        "final_text_hash": final_text_hash,
        "final_transcript": comparison.final_transcript,
        "confidence_score": comparison.confidence_score,
        "agreement_score": comparison.agreement_score,
        "engines": [r.to_dict() for r in results],
        "differences": comparison.differences,
        "report_path": report_path,
    }
