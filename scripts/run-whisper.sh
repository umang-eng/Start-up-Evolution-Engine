#!/usr/bin/env bash
set -euo pipefail

WHISPER_DIR="${WHISPER_CPP_DIR:-$HOME/whisper.cpp}"
WHISPER_SERVER="$WHISPER_DIR/build/bin/whisper-server"
WHISPER_MODEL="${WHISPER_MODEL_PATH:-$WHISPER_DIR/models/ggml-base.bin}"

if [[ ! -x "$WHISPER_SERVER" ]]; then
  echo "whisper.cpp server not found: $WHISPER_SERVER" >&2
  echo "Follow WHISPER_CPP_SETUP.md or set WHISPER_CPP_DIR to your whisper.cpp checkout." >&2
  exit 1
fi

if [[ ! -f "$WHISPER_MODEL" ]]; then
  echo "Whisper model not found: $WHISPER_MODEL" >&2
  echo "Download the base model using whisper.cpp/models/download-ggml-model.sh base." >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg is required for audio transcription. Install it and try again." >&2
  exit 1
fi

exec "$WHISPER_SERVER" \
  --model "$WHISPER_MODEL" \
  --host 127.0.0.1 \
  --port 8080
