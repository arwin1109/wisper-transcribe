import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.models.schemas import CreateSessionRequest


class SessionNotFoundError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class SessionStorage:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, request: CreateSessionRequest) -> dict:
        session_id = str(uuid4())
        created_at = utc_now()
        session_dir = self._session_dir(session_id)
        (session_dir / "chunks").mkdir(parents=True, exist_ok=False)
        (session_dir / "transcript.txt").write_text("", encoding="utf-8")

        metadata = {
            "session_id": session_id,
            "status": "active",
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "completed_at": None,
            "title": request.title,
            "source": request.source,
            "metadata": request.metadata,
            "chunks": [],
        }
        self._write_metadata(session_id, metadata)
        return metadata

    def get_session(self, session_id: str) -> dict:
        metadata_path = self._metadata_path(session_id)
        if not metadata_path.exists():
            raise SessionNotFoundError(session_id)
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    async def save_chunk(
        self,
        session_id: str,
        upload: UploadFile,
        max_bytes: int | None = None,
    ) -> tuple[str, Path]:
        metadata = self.get_session(session_id)
        chunk_id = f"{len(metadata['chunks']) + 1:06d}-{uuid4().hex}"
        suffix = Path(upload.filename or "").suffix or ".audio"
        chunk_path = self._session_dir(session_id) / "chunks" / f"{chunk_id}{suffix}"

        bytes_written = 0
        with chunk_path.open("wb") as destination:
            while content := await upload.read(1024 * 1024):
                bytes_written += len(content)
                if max_bytes is not None and bytes_written > max_bytes:
                    chunk_path.unlink(missing_ok=True)
                    raise UploadTooLargeError(upload.filename or "audio")
                destination.write(content)

        now = utc_now().isoformat()
        metadata["chunks"].append(
            {
                "chunk_id": chunk_id,
                "filename": upload.filename,
                "path": str(chunk_path),
                "uploaded_at": now,
                "transcribed_at": None,
            }
        )
        metadata["updated_at"] = now
        self._write_metadata(session_id, metadata)
        return chunk_id, chunk_path

    def append_transcript(self, session_id: str, chunk_id: str, text: str) -> None:
        metadata = self.get_session(session_id)
        now = utc_now().isoformat()

        transcript_path = self._transcript_path(session_id)
        with transcript_path.open("a", encoding="utf-8") as transcript:
            transcript.write(f"[{now}] chunk={chunk_id}\n")
            transcript.write(text.strip())
            transcript.write("\n\n")

        for chunk in metadata["chunks"]:
            if chunk["chunk_id"] == chunk_id:
                chunk["transcribed_at"] = now
                break
        metadata["updated_at"] = now
        self._write_metadata(session_id, metadata)

    def complete_session(self, session_id: str) -> dict:
        metadata = self.get_session(session_id)
        completed_at = utc_now()
        metadata["status"] = "completed"
        metadata["completed_at"] = completed_at.isoformat()
        metadata["updated_at"] = completed_at.isoformat()
        self._write_metadata(session_id, metadata)
        return metadata

    def reset(self) -> None:
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def transcript_path(self, session_id: str) -> Path:
        self.get_session(session_id)
        return self._transcript_path(session_id)

    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def _metadata_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "metadata.json"

    def _transcript_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "transcript.txt"

    def _write_metadata(self, session_id: str, metadata: dict) -> None:
        self._metadata_path(session_id).write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
