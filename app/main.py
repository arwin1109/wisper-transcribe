from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Whisper Transcribe",
    version="0.1.0",
    description="Self-hosted meeting audio transcription API.",
)
app.include_router(router)

