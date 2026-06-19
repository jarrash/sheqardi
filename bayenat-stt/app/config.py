"""Application configuration for Bayenat / بيّنات.

All values can be overridden through environment variables (or a ``.env`` file).
See ``.env.example`` for the full list.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Set

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: .../bayenat-stt
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---------------------------------------------------------
    app_name: str = "Bayenat STT"
    app_version: str = "0.1.0"
    default_language: str = "ar"

    # --- Upload constraints ---------------------------------------------
    max_file_size_mb: int = 200
    allowed_extensions: Set[str] = {"mp3", "wav", "m4a"}

    # --- Engine configuration -------------------------------------------
    # Model size can be lowered (e.g. "small", "base") for local testing to
    # avoid downloading the multi-GB large-v3 weights.
    faster_whisper_model: str = "large-v3"
    whisper_model: str = "large-v3"
    # "auto" -> use CUDA when available, otherwise CPU.
    device: str = "auto"

    # Third engine is a safe placeholder until a concrete backend
    # (NVIDIA Parakeet, a HuggingFace Arabic model, an external STT API) is wired up.
    third_engine_enabled: bool = False

    # --- Storage ---------------------------------------------------------
    upload_dir: Path = BASE_DIR / "app" / "storage" / "uploads"
    report_dir: Path = BASE_DIR / "app" / "storage" / "reports"
    db_path: Path = BASE_DIR / "app" / "storage" / "bayenat.db"

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def _normalise_extensions(cls, value):
        """Accept a comma-separated string from the environment as well as a set."""
        if isinstance(value, str):
            return {ext.strip().lower().lstrip(".") for ext in value.split(",") if ext.strip()}
        return {str(ext).lower().lstrip(".") for ext in value}

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create the storage directories if they do not yet exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


settings = get_settings()
