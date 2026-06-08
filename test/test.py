#!/usr/bin/env python3
"""Smoke test the Whisper transcription API against files in sample-audios."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO_DIR = BASE_DIR / "sample-audios"
SUPPORTED_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".mp4", ".ogg", ".opus", ".wav", ".webm"}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request_json(
    method: str,
    url: str,
    api_key: str | None = None,
    payload: dict | None = None,
) -> dict:
    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if api_key:
        headers["X-API-Key"] = api_key

    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def upload_audio(url: str, api_key: str, audio_path: Path) -> dict:
    boundary = "----whisper-transcribe-test-boundary"
    content_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    audio_bytes = audio_path.read_bytes()

    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="audio"; filename="{audio_path.name}"\r\n'.encode(
                "utf-8"
            ),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            audio_bytes,
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
    )

    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-API-Key": api_key,
        },
        method="POST",
    )

    with urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def audio_files(audio_dir: Path) -> list[Path]:
    if not audio_dir.exists():
        return []

    return sorted(
        path
        for path in audio_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    base_url = os.getenv("WHISPER_TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    api_key = os.getenv("WHISPER_API_KEY")
    audio_dir = Path(os.getenv("WHISPER_TEST_AUDIO_DIR", str(DEFAULT_AUDIO_DIR)))

    if not api_key:
        print("Missing WHISPER_API_KEY. Set it in .env or export it before running.")
        return 1

    files = audio_files(audio_dir)
    if not files:
        print(f"No supported audio files found in {audio_dir}")
        return 1

    try:
        health = request_json("GET", f"{base_url}/health")
        print(f"health: {health.get('status')}")

        session = request_json(
            "POST",
            f"{base_url}/api/v1/sessions",
            api_key=api_key,
            payload={"title": "Whisper smoke test", "source": "test/test.py"},
        )
        session_id = session["session_id"]
        print(f"session: {session_id}")

        failures = 0
        for audio_path in files:
            print(f"transcribing: {audio_path.name}")
            result = upload_audio(
                f"{base_url}/api/v1/sessions/{session_id}/transcribe",
                api_key,
                audio_path,
            )
            text = result.get("text", "").strip()
            language = result.get("language") or "unknown"
            seconds = result.get("metrics", {}).get("processing_time_seconds")

            if text:
                print(f"ok: {audio_path.name} language={language} seconds={seconds}")
                print(f"text: {text[:240]}")
            else:
                failures += 1
                print(f"failed: {audio_path.name} returned empty transcript")

        request_json("POST", f"{base_url}/api/v1/sessions/{session_id}/complete", api_key=api_key)
        return 1 if failures else 0
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        print(f"HTTP {error.code}: {detail}")
        return 1
    except URLError as error:
        print(f"Could not reach API at {base_url}: {error.reason}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

