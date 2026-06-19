"""FastAPI application entry point for Bayenat / بيّنات."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.models.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bayenat")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Prepare storage and database on startup."""
    settings.ensure_dirs()
    init_db()
    logger.info("%s %s started.", settings.app_name, settings.app_version)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Bayenat / بيّنات — turn audio evidence into verifiable, reviewable "
        "transcripts using multiple speech-to-text engines with cross-engine "
        "comparison and a chain-of-custody report."
    ),
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
