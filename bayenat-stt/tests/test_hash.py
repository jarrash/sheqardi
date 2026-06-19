"""Tests for the hashing service."""

import hashlib

from app.services import hash_service


def test_sha256_bytes_matches_hashlib():
    data = b"bayenat evidence"
    assert hash_service.sha256_bytes(data) == hashlib.sha256(data).hexdigest()


def test_sha256_text_is_utf8():
    text = "بيّنات"  # Arabic, multibyte
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert hash_service.sha256_text(text) == expected


def test_sha256_text_is_deterministic():
    assert hash_service.sha256_text("hello") == hash_service.sha256_text("hello")
    assert hash_service.sha256_text("hello") != hash_service.sha256_text("world")


def test_sha256_file(tmp_path):
    payload = b"\x00\x01\x02 audio bytes \xff"
    file_path = tmp_path / "audio.wav"
    file_path.write_bytes(payload)
    assert hash_service.sha256_file(file_path) == hashlib.sha256(payload).hexdigest()
