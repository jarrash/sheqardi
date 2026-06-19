"""API routes for Bayenat / بيّنات."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.models.schemas import HealthResponse, TranscribeResponse
from app.services import transcription_service
from app.services.audio_service import AudioValidationError, save_upload

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(app=settings.app_name, version=settings.app_version)


@router.post(
    "/api/v1/transcribe",
    response_model=TranscribeResponse,
    tags=["transcription"],
    summary="Transcribe an audio evidence file using multiple STT engines",
)
async def transcribe(
    file: UploadFile = File(..., description="Audio file (mp3, wav, m4a)"),
    language: str = Form(settings.default_language, description="Language code, e.g. 'ar'"),
    case_id: Optional[str] = Form(None),
    evidence_id: Optional[str] = Form(None),
) -> TranscribeResponse:
    """Validate, transcribe, compare and report on an audio evidence file."""
    # 1. Validate + persist the upload (size limit enforced while streaming).
    try:
        saved = save_upload(file.file, file.filename or "")
    except AudioValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    # 2. Run the pipeline.
    try:
        payload = await transcription_service.transcribe_audio(
            audio_path=saved["audio_path"],
            original_filename=saved["original_filename"],
            uploaded_at=saved["uploaded_at"],
            language=language,
            case_id=case_id,
            evidence_id=evidence_id,
        )
    except ValueError as exc:
        # No engine produced a usable transcript.
        logger.error("Transcription failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Transcription failed: {exc}",
        ) from exc

    return TranscribeResponse(**payload)
