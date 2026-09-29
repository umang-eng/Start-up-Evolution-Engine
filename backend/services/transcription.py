"""Audio preprocessing and transcription through the local whisper.cpp server."""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx

from backend.core.config import settings
from backend.core.logging import logger


def _input_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ".audio"


async def _convert_to_whisper_wav(audio_bytes: bytes, filename: str) -> bytes:
    """Convert an uploaded audio file to mono, 16 kHz, signed 16-bit PCM WAV."""
    with tempfile.TemporaryDirectory(prefix="see-transcription-") as temp_dir:
        input_path = Path(temp_dir) / f"input{_input_suffix(filename)}"
        output_path = Path(temp_dir) / "audio-16khz-mono.wav"
        input_path.write_bytes(audio_bytes)

        try:
            process = await asyncio.create_subprocess_exec(
                settings.FFMPEG_BINARY,
                "-nostdin",
                "-v",
                "error",
                "-y",
                "-i",
                str(input_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ValueError(
                f"FFmpeg was not found. Install it or set FFMPEG_BINARY "
                f"(currently '{settings.FFMPEG_BINARY}')."
            ) from exc
        except OSError as exc:
            raise ValueError("FFmpeg could not be started. Check FFMPEG_BINARY and executable permissions.") from exc

        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise ValueError("Audio conversion timed out. Try a shorter recording.") from exc
        except asyncio.CancelledError:
            process.kill()
            await process.communicate()
            raise

        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            logger.warning("FFmpeg could not convert uploaded audio: %s", detail[:500])
            raise ValueError(
                "Audio could not be converted. Upload a valid audio file "
                "(for example WebM, MP3, M4A, OGG, FLAC, or WAV)."
            )

        try:
            return output_path.read_bytes()
        except OSError as exc:
            logger.error("FFmpeg did not produce its expected WAV output")
            raise ValueError("Audio conversion failed to produce a WAV file.") from exc


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> dict[str, Any]:
    """Convert audio to whisper.cpp's WAV requirements and return its JSON transcript."""
    if not audio_bytes:
        raise ValueError("The uploaded audio file is empty.")

    wav_bytes = await _convert_to_whisper_wav(audio_bytes, filename)
    whisper_url = f"{settings.WHISPER_HOST.rstrip('/')}/inference"
    form_data = {"response_format": "json"}
    if language:
        form_data["language"] = language
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}

    try:
        timeout = httpx.Timeout(settings.WHISPER_TIMEOUT_SECONDS, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(whisper_url, files=files, data=form_data)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.error("whisper.cpp transcription timed out at %s", whisper_url)
        raise ValueError("Transcription timed out. Try a shorter recording or increase WHISPER_TIMEOUT_SECONDS.") from exc
    except httpx.ConnectError as exc:
        logger.error("whisper.cpp server is unreachable at %s", whisper_url)
        raise ValueError(
            "The local whisper.cpp server is unavailable. Start it and verify WHISPER_HOST "
            f"(currently '{settings.WHISPER_HOST}')."
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error("whisper.cpp returned HTTP %s: %s", exc.response.status_code, exc.response.text[:500])
        raise ValueError(f"whisper.cpp transcription failed with HTTP {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        logger.error("whisper.cpp request failed: %s", exc)
        raise ValueError("Could not send audio to the local whisper.cpp server.") from exc

    try:
        result = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("whisper.cpp returned a non-JSON response")
        raise ValueError("The whisper.cpp server returned an invalid JSON response.") from exc

    if not isinstance(result, dict):
        raise ValueError("The whisper.cpp server returned an unexpected response.")

    text = result.get("text")
    if not isinstance(text, str):
        raise ValueError("The whisper.cpp response did not include transcript text.")

    segments = result.get("segments", [])
    if not isinstance(segments, list):
        segments = []
    duration = result.get("duration", 0)
    if not isinstance(duration, (int, float)):
        duration = 0
    return {
        "text": text,
        "segments": [
            {
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "text": segment.get("text", ""),
            }
            for segment in segments
            if isinstance(segment, dict)
        ],
        "language": result.get("language", language or "unknown"),
        "duration": duration,
    }


async def transcribe_audio_file(file_path: str | Path) -> str:
    """Read an audio file, transcribe it through whisper.cpp, and return the text."""
    path = Path(file_path)
    try:
        audio_bytes = await asyncio.to_thread(path.read_bytes)
    except OSError as exc:
        raise ValueError(f"Could not read audio file '{path}'.") from exc
    result = await transcribe_audio(audio_bytes, filename=path.name)
    return result["text"].strip()
