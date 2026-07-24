"""
Transcription Service — Sends audio to Whisper.cpp for speech-to-text.
"""

import httpx
from backend.core.config import settings
from backend.core.logging import logger


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> dict:
    """
    Send audio to Whisper.cpp server for transcription.

    Returns:
        {
            "text": "full transcribed text",
            "segments": [{"start": 0.0, "end": 2.5, "text": "..."}],
            "language": "en"
        }
    """
    whisper_url = f"{settings.WHISPER_HOST}/v1/audio/transcriptions"

    # Determine content type from filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    content_types = {
        "webm": "audio/webm",
        "mp4": "audio/mp4",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "flac": "audio/flac",
    }
    content_type = content_types.get(ext, "audio/webm")

    files = {"file": (filename, audio_bytes, content_type)}
    data = {"response_format": "verbose_json"}
    if language:
        data["language"] = language

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {}
            if settings.WHISPER_API_KEY:
                headers["Authorization"] = f"Bearer {settings.WHISPER_API_KEY}"
            response = await client.post(whisper_url, files=files, data=data, headers=headers)
            response.raise_for_status()

            result = response.json()

            # Whisper API returns different formats depending on response_format
            # verbose_json returns: {text, segments, language, duration}
            if isinstance(result, dict):
                return {
                    "text": result.get("text", ""),
                    "segments": [
                        {
                            "start": seg.get("start", 0),
                            "end": seg.get("end", 0),
                            "text": seg.get("text", ""),
                        }
                        for seg in result.get("segments", [])
                    ],
                    "language": result.get("language", "unknown"),
                    "duration": result.get("duration", 0),
                }
            else:
                # Fallback for simple text response
                return {
                    "text": str(result),
                    "segments": [],
                    "language": "unknown",
                    "duration": 0,
                }

    except httpx.TimeoutException:
        logger.error("Whisper transcription timed out")
        raise ValueError("Transcription timed out. Audio may be too long.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Whisper API error: {e.response.status_code} - {e.response.text}")
        raise ValueError(f"Transcription failed: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise ValueError(f"Transcription service unavailable: {str(e)}")
