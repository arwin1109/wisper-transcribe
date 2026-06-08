from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "whisper-transcribe"


class CreateSessionRequest(BaseModel):
    title: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    source: str | None = None


class ProcessingMetrics(BaseModel):
    audio_duration_seconds: float | None = None
    processing_time_seconds: float


class TranscriptionResponse(BaseModel):
    session_id: str
    chunk_id: str
    text: str
    language: str | None = None
    metrics: ProcessingMetrics


class CompleteSessionResponse(BaseModel):
    session_id: str
    status: str
    completed_at: datetime
    transcript_path: str

