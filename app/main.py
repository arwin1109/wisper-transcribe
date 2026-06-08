from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import get_transcriber
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload Whisper model on startup (unless overridden, e.g. in tests)
    if get_transcriber not in app.dependency_overrides:
        _ = get_transcriber().model
    yield


app = FastAPI(
    title="Whisper Transcribe",
    version="0.1.0",
    description="Self-hosted meeting audio transcription API.",
    lifespan=lifespan,
)
app.include_router(router)

