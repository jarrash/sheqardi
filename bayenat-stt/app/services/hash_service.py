"""SHA-256 hashing helpers for the chain of custody.

Audio files and final transcripts are fingerprinted so a report can be verified
later: re-hashing the stored artefact must reproduce the recorded digest.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 digest of ``text`` (UTF-8 encoded)."""
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Union[str, Path]) -> str:
    """Return the hex SHA-256 digest of a file, read in chunks to bound memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
