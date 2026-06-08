#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="${APP_NAME:-whisper-transcribe}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
DATA_DIR="${WHISPER_DATA_DIR:-$APP_DIR/data}"

export WHISPER_DATA_DIR="$DATA_DIR"
export WHISPER_MODEL_NAME="${WHISPER_MODEL_NAME:-large-v3-turbo}"
export WHISPER_DEVICE="${WHISPER_DEVICE:-cpu}"
export WHISPER_COMPUTE_TYPE="${WHISPER_COMPUTE_TYPE:-int8}"
export WHISPER_LOG_LEVEL="${WHISPER_LOG_LEVEL:-INFO}"

log() {
  printf '[deploy] %s\n' "$*"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[deploy] missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

require_command "$PYTHON_BIN"
require_command pm2

cd "$APP_DIR"
mkdir -p "$DATA_DIR/sessions"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  log "creating virtualenv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

log "upgrading pip"
"$VENV_DIR/bin/python" -m pip install --upgrade pip

log "installing application dependencies"
"$VENV_DIR/bin/pip" install -e .

UVICORN_BIN="$VENV_DIR/bin/uvicorn"
if [ ! -x "$UVICORN_BIN" ]; then
  printf '[deploy] uvicorn was not installed at %s\n' "$UVICORN_BIN" >&2
  exit 1
fi

log "starting or reloading PM2 app $APP_NAME"
if pm2 describe "$APP_NAME" >/dev/null 2>&1; then
  pm2 restart "$APP_NAME" --update-env
else
  pm2 start "$UVICORN_BIN" \
    --name "$APP_NAME" \
    --interpreter none \
    -- app.main:app --host "$HOST" --port "$PORT"
fi

pm2 save

log "deployment complete"
log "health: http://127.0.0.1:$PORT/health"

