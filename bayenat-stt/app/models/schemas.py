"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EngineResultSchema(BaseModel):
    """A single engine's contribution, as returned to the client."""

    engine_name: str
    language: str
    text: str
    processing_time_seconds: float
    success: bool = True
    error: Optional[str] = None
    version: Optional[str] = None


class DifferenceSchema(BaseModel):
    engine_a: str
    engine_b: str
    similarity: float
    word_error_rate: Optional[float] = None
    length_a: int
    length_b: int


class TranscribeResponse(BaseModel):
    """Response body for ``POST /api/v1/transcribe``."""

    case_id: Optional[str] = None
    evidence_id: Optional[str] = None
    audio_hash: str
    final_text_hash: str
    final_transcript: str
    confidence_score: float = Field(..., description="0-100 percentage")
    agreement_score: float = Field(..., description="0-1 average pairwise agreement")
    engines: List[EngineResultSchema]
    differences: List[DifferenceSchema] = Field(default_factory=list)
    report_path: str


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
