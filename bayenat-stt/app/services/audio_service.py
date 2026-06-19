"""Audio upload validation and persistence.

Responsible for rejecting non-audio / oversized uploads and saving accepted
files to local storage under a collision-free name.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from app.config import settings

logger = logging.getLogger(__name__)


class AudioValidationError(ValueError):
    """Raised when an upload is not an accepted audio file or exceeds the size limit."""


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_filename(filename: str | None) -> str:
    """Validate the extension and return it; raise :class:`AudioValidationError` otherwise."""
    if not filename:
        raise AudioValidationError("No filename provided.")
    ext = _extension(filename)
    if ext not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise AudioValidationError(
            f"Unsupported file type '.{ext}'. Allowed types: {allowed}."
        )
    return ext


def save_upload(file_obj: BinaryIO, original_filename: str) -> dict:
    """Stream ``file_obj`` to disk, enforcing the size limit.

    Returns a dict with ``audio_path``, ``original_filename``, ``stored_filename``
    and ``uploaded_at`` (ISO-8601, UTC).
    """
    ext = validate_filename(original_filename)
    settings.ensure_dirs()

    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    destination = settings.upload_dir / stored_filename
    max_bytes = settings.max_file_size_bytes

    total = 0
    chunk_size = 1024 * 1024
    try:
        with open(destination, "wb") as out:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise AudioValidationError(
                        f"File exceeds the maximum size of {settings.max_file_size_mb} MB."
                    )
                out.write(chunk)
    except AudioValidationError:
        destination.unlink(missing_ok=True)
        raise

    if total == 0:
        destination.unlink(missing_ok=True)
        raise AudioValidationError("Uploaded file is empty.")

    logger.info("Saved upload %s (%d bytes) -> %s", original_filename, total, destination)
    return {
        "audio_path": str(destination),
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "size_bytes": total,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
