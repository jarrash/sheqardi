"""API tests using FastAPI's TestClient with engines stubbed out.

No real models are downloaded: ``default_engines`` is monkeypatched to return
lightweight stub engines, and storage/DB paths are redirected to a tmp dir.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.engines.base import BaseEngine
from app.main import app
from app.services import transcription_service


class StubEngine(BaseEngine):
    def __init__(self, name: str, text: str):
        self.name = name
        self._text = text

    def _transcribe(self, audio_path: str, language: str) -> str:
        return self._text


@pytest.fixture(autouse=True)
def _redirect_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "report_dir", tmp_path / "reports")
    monkeypatch.setattr(settings, "db_path", tmp_path / "bayenat.db")
    settings.ensure_dirs()
    yield


@pytest.fixture(autouse=True)
def _stub_engines(monkeypatch):
    monkeypatch.setattr(
        transcription_service,
        "default_engines",
        lambda: [
            StubEngine("faster-whisper-stub", "هذا نص الدليل الصوتي"),
            StubEngine("whisper-stub", "هذا نص الدليل الصوتي"),
            StubEngine("third-stub", "هذا نص الدليل الصوتي المختلف"),
        ],
    )
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_transcribe_happy_path(client):
    audio = io.BytesIO(b"fake audio bytes")
    resp = client.post(
        "/api/v1/transcribe",
        files={"file": ("evidence.wav", audio, "audio/wav")},
        data={"language": "ar", "case_id": "C-1", "evidence_id": "E-9"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["case_id"] == "C-1"
    assert body["evidence_id"] == "E-9"
    assert len(body["audio_hash"]) == 64
    assert len(body["final_text_hash"]) == 64
    assert body["final_transcript"]
    assert 0 <= body["agreement_score"] <= 1
    assert 0 <= body["confidence_score"] <= 100
    assert len(body["engines"]) == 3
    assert body["report_path"].endswith(".json")

    # Report file was actually written.
    report_files = list((settings.report_dir).glob("*.json"))
    assert len(report_files) == 1


def test_transcribe_rejects_non_audio(client):
    resp = client.post(
        "/api/v1/transcribe",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_transcribe_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setattr(settings, "max_file_size_mb", 0)  # 0 MB -> everything too big
    resp = client.post(
        "/api/v1/transcribe",
        files={"file": ("big.wav", io.BytesIO(b"x" * 1024), "audio/wav")},
    )
    assert resp.status_code == 400


def test_transcribe_persists_db_record(client):
    audio = io.BytesIO(b"fake audio bytes")
    client.post(
        "/api/v1/transcribe",
        files={"file": ("evidence.wav", audio, "audio/wav")},
        data={"language": "ar"},
    )
    from app.models.database import get_record

    record = get_record(1, db_path=settings.db_path)
    assert record is not None
    assert record["original_filename"] == "evidence.wav"
    assert len(record["audio_hash"]) == 64
