"""SQLite persistence for transcription records.

Uses the stdlib ``sqlite3`` driver — no ORM is needed for the MVP. The schema is
deliberately small; richer entities (cases, users, audit trail) can be added when
multi-tenancy / RBAC land.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id           TEXT,
    evidence_id       TEXT,
    original_filename TEXT NOT NULL,
    audio_path        TEXT NOT NULL,
    report_path       TEXT,
    audio_hash        TEXT NOT NULL,
    final_text_hash   TEXT,
    confidence_score  REAL,
    created_at        TEXT NOT NULL
);
"""


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Create the database schema if it does not exist."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
    logger.info("SQLite initialised at %s", db_path or settings.db_path)


def insert_record(
    *,
    case_id: Optional[str],
    evidence_id: Optional[str],
    original_filename: str,
    audio_path: str,
    report_path: Optional[str],
    audio_hash: str,
    final_text_hash: Optional[str],
    confidence_score: Optional[float],
    db_path: Optional[Path] = None,
) -> int:
    """Insert a transcription record and return its row id."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO transcriptions (
                case_id, evidence_id, original_filename, audio_path, report_path,
                audio_hash, final_text_hash, confidence_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                evidence_id,
                original_filename,
                audio_path,
                report_path,
                audio_hash,
                final_text_hash,
                confidence_score,
                created_at,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_record(record_id: int, db_path: Optional[Path] = None) -> Optional[dict]:
    """Fetch a single record by id (mainly for tests / future read endpoints)."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM transcriptions WHERE id = ?", (record_id,)
        ).fetchone()
        return dict(row) if row else None
