"""Chain-of-custody report generation.

Builds a self-contained JSON record of a transcription run — timestamps, hashes,
per-engine output, engine versions, errors and metadata — and persists it so the
result can be audited or re-verified later.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from app.config import BASE_DIR, settings
from app.engines.base import EngineResult
from app.services.comparison_service import ComparisonResult

logger = logging.getLogger(__name__)

REPORT_SCHEMA_VERSION = "1.0"


def build_report(
    *,
    original_filename: str,
    uploaded_at: str,
    processing_started_at: str,
    processing_finished_at: str,
    audio_hash: str,
    final_text_hash: str,
    engine_results: List[EngineResult],
    comparison: ComparisonResult,
    case_id: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> dict:
    """Assemble the chain-of-custody report dictionary."""
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generator": f"{settings.app_name} {settings.app_version}",
        "metadata": {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "original_filename": original_filename,
        },
        "timestamps": {
            "uploaded_at": uploaded_at,
            "processing_started_at": processing_started_at,
            "processing_finished_at": processing_finished_at,
        },
        "hashes": {
            "audio_sha256": audio_hash,
            "final_text_sha256": final_text_hash,
        },
        "result": {
            "final_transcript": comparison.final_transcript,
            "final_engine": comparison.final_engine,
            "confidence_score": comparison.confidence_score,
            "agreement_score": comparison.agreement_score,
        },
        "engines": [r.to_dict() for r in engine_results],
        "engine_errors": [
            {"engine_name": r.engine_name, "error": r.error}
            for r in engine_results
            if not r.success
        ],
        "differences": comparison.differences,
    }


def save_report(report: dict, report_dir: Optional[Path] = None) -> str:
    """Persist ``report`` as JSON and return a path relative to the project root."""
    target_dir = Path(report_dir) if report_dir else settings.report_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.json"
    full_path = target_dir / filename
    with open(full_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    logger.info("Report written to %s", full_path)
    # Return a stable, project-relative path for the API response.
    try:
        return str(full_path.relative_to(BASE_DIR))
    except ValueError:
        return str(full_path)
