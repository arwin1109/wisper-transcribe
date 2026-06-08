from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.api.auth import require_api_key
from app.core.config import Settings, get_settings
from app.api.dependencies import get_storage, get_transcriber
from app.models.schemas import (
    CompleteSessionResponse,
    CreateSessionRequest,
    HealthResponse,
    ProcessingMetrics,
    SessionResponse,
    TranscriptionResponse,
)
from app.services.storage import SessionNotFoundError, SessionStorage, UploadTooLargeError
from app.services.transcriber import FasterWhisperTranscriber

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/api/v1/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_session(
    request: CreateSessionRequest,
    storage: SessionStorage = Depends(get_storage),
) -> SessionResponse:
    metadata = storage.create_session(request)
    logger.info("session_created", session_id=metadata["session_id"])
    return _session_response(metadata)


@router.post(
    "/api/v1/sessions/{session_id}/transcribe",
    response_model=TranscriptionResponse,
    dependencies=[Depends(require_api_key)],
)
async def transcribe_chunk(
    session_id: UUID,
    audio: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    storage: SessionStorage = Depends(get_storage),
    transcriber: FasterWhisperTranscriber = Depends(get_transcriber),
) -> TranscriptionResponse:
    session_id_value = str(session_id)
    try:
        chunk_id, chunk_path = await storage.save_chunk(
            session_id_value,
            audio,
            max_bytes=settings.max_upload_mb * 1024 * 1024,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Audio upload exceeds {settings.max_upload_mb} MB",
        ) from exc
    finally:
        await audio.close()

    logger.info(
        "chunk_transcription_started",
        session_id=session_id_value,
        chunk_id=chunk_id,
        filename=audio.filename,
        model_name=getattr(transcriber, "model_name", None),
        device=getattr(transcriber, "device", None),
        compute_type=getattr(transcriber, "compute_type", None),
    )
    result = await run_in_threadpool(transcriber.transcribe, chunk_path)
    storage.append_transcript(session_id_value, chunk_id, result.text)
    logger.info(
        "chunk_transcribed",
        session_id=session_id_value,
        chunk_id=chunk_id,
        processing_time_seconds=result.processing_time_seconds,
    )

    return TranscriptionResponse(
        session_id=session_id_value,
        chunk_id=chunk_id,
        text=result.text,
        language=result.language,
        metrics=ProcessingMetrics(
            audio_duration_seconds=result.audio_duration_seconds,
            processing_time_seconds=result.processing_time_seconds,
        ),
    )


@router.post(
    "/api/v1/sessions/{session_id}/complete",
    response_model=CompleteSessionResponse,
    dependencies=[Depends(require_api_key)],
)
def complete_session(
    session_id: UUID,
    storage: SessionStorage = Depends(get_storage),
) -> CompleteSessionResponse:
    session_id_value = str(session_id)
    try:
        metadata = storage.complete_session(session_id_value)
        transcript_path = storage.transcript_path(session_id_value)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc

    logger.info("session_completed", session_id=session_id_value)
    return CompleteSessionResponse(
        session_id=session_id_value,
        status=metadata["status"],
        completed_at=datetime.fromisoformat(metadata["completed_at"]),
        transcript_path=str(transcript_path),
    )


def _session_response(metadata: dict) -> SessionResponse:
    return SessionResponse(
        session_id=metadata["session_id"],
        status=metadata["status"],
        created_at=datetime.fromisoformat(metadata["created_at"]),
        updated_at=datetime.fromisoformat(metadata["updated_at"]),
        title=metadata["title"],
        source=metadata["source"],
    )
