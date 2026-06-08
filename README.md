# Whisper Transcribe

Sprint 1 implementation of the Obsidian Meeting Intelligence Platform foundation: a self-hosted FastAPI service that stores meeting sessions, accepts audio chunks, transcribes them with Faster-Whisper, and persists transcripts chronologically.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## PM2 Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

The script creates `.venv`, installs the app, creates the data directory, and starts or restarts `whisper-transcribe` in PM2.
If `.env` does not exist, it also creates one with a generated `WHISPER_API_KEY`.

Common overrides:

```bash
APP_NAME=whisper-transcribe PORT=8000 WHISPER_DATA_DIR=/data ./deploy.sh
```

Health check:

```bash
curl http://localhost:8000/health
```

Create a session:

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "X-API-Key: your-secret" \
  -H "Content-Type: application/json" \
  -d '{"title":"Weekly sync","source":"obsidian"}'
```

Upload an audio chunk:

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/transcribe \
  -H "X-API-Key: your-secret" \
  -F "audio=@chunk.wav"
```

Complete a session:

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/complete \
  -H "X-API-Key: your-secret"
```

## Configuration

Environment variables:

- `WHISPER_API_KEY`: required API key for protected endpoints
- `WHISPER_DATA_DIR`: session storage directory, default `./data`
- `WHISPER_MODEL_NAME`: Faster-Whisper model, default `large-v3-turbo`
- `WHISPER_DEVICE`: default `cpu`
- `WHISPER_COMPUTE_TYPE`: default `int8`
- `WHISPER_LOG_LEVEL`: default `INFO`

Create a local `.env` file:

```bash
cp .env.example .env
```

Then replace `WHISPER_API_KEY` with a long random secret. All `/api/v1/*` endpoints require this header:

```text
X-API-Key: your-secret
```

Session files are stored under:

```text
{WHISPER_DATA_DIR}/sessions/{session_id}/metadata.json
{WHISPER_DATA_DIR}/sessions/{session_id}/transcript.txt
{WHISPER_DATA_DIR}/sessions/{session_id}/chunks/
```

## Tests

```bash
pytest
```

## Whisper Smoke Test

Place sample audio files in `sample-audios/`, start the API, then run:

```bash
python test/test.py
```

The script reads `WHISPER_API_KEY` from `.env` and sends each supported audio file to the transcription endpoint.
