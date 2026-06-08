from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_storage, get_transcriber
from app.main import app
from app.services.storage import SessionStorage
from app.services.transcriber import TranscriptionResult


class FakeTranscriber:
    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        return TranscriptionResult(
            text=f"transcribed {audio_path.name}",
            language="en",
            audio_duration_seconds=10.0,
            processing_time_seconds=0.25,
        )


@pytest.fixture()
def client(tmp_path):
    storage = SessionStorage(tmp_path)

    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_transcriber] = lambda: FakeTranscriber()

    with TestClient(app) as test_client:
        yield test_client, storage

    app.dependency_overrides.clear()


def test_health(client):
    test_client, _ = client

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_lifecycle_persists_transcript(client):
    test_client, storage = client

    create_response = test_client.post(
        "/api/v1/sessions",
        json={"title": "Weekly sync", "source": "obsidian"},
    )
    assert create_response.status_code == 201
    session = create_response.json()
    session_id = session["session_id"]

    transcribe_response = test_client.post(
        f"/api/v1/sessions/{session_id}/transcribe",
        files={"audio": ("chunk.wav", b"fake audio", "audio/wav")},
    )
    assert transcribe_response.status_code == 200
    transcription = transcribe_response.json()
    assert transcription["session_id"] == session_id
    assert transcription["language"] == "en"
    assert transcription["metrics"]["audio_duration_seconds"] == 10.0
    assert "transcribed" in transcription["text"]

    transcript_text = storage.transcript_path(session_id).read_text(encoding="utf-8")
    assert transcription["chunk_id"] in transcript_text
    assert transcription["text"] in transcript_text

    complete_response = test_client.post(f"/api/v1/sessions/{session_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_unknown_session_returns_404(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/transcribe",
        files={"audio": ("chunk.wav", b"fake audio", "audio/wav")},
    )

    assert response.status_code == 404


def test_invalid_session_id_returns_422(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/sessions/not-a-uuid/transcribe",
        files={"audio": ("chunk.wav", b"fake audio", "audio/wav")},
    )

    assert response.status_code == 422
