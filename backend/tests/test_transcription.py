import io
import shutil
import wave

import httpx
import pytest

from backend.core.config import settings
from backend.services import transcription


pytestmark = pytest.mark.asyncio


def _make_test_wav() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00\x00\x00" * 800)
    return output.getvalue()


async def test_conversion_normalizes_audio_to_whisper_wav_format() -> None:
    if shutil.which(settings.FFMPEG_BINARY) is None:
        pytest.skip("FFmpeg is required for the audio conversion test")

    converted = await transcription._convert_to_whisper_wav(_make_test_wav(), "recording.wav")

    with wave.open(io.BytesIO(converted), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 16000


async def test_transcription_posts_wav_to_whisper_cpp_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def convert_audio(*args: object, **kwargs: object) -> bytes:
        return b"normalized-wav"

    monkeypatch.setattr(transcription, "_convert_to_whisper_wav", convert_audio)
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            200,
            json={
                "text": "  Meeting notes  ",
                "language": "en",
                "duration": 4.5,
                "segments": [{"start": 0, "end": 4.5, "text": "Meeting notes"}],
            },
        )

    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        transcription.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    result = await transcription.transcribe_audio(b"source-audio", "recording.m4a", "en")

    request = captured["request"]
    body = request.content.decode("latin-1")
    assert request.url.path == "/inference"
    assert 'name="file"; filename="audio.wav"' in body
    assert 'name="response_format"' in body
    assert "json" in body
    assert result["text"].strip() == "Meeting notes"
    assert result["language"] == "en"
    assert result["duration"] == 4.5
    assert result["segments"][0]["text"] == "Meeting notes"


async def test_transcribe_audio_file_reads_path_and_returns_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    audio_path = tmp_path / "recording.mp3"
    audio_path.write_bytes(b"audio")
    captured: dict[str, object] = {}

    async def transcribe(audio_bytes: bytes, filename: str) -> dict[str, str]:
        captured["audio_bytes"] = audio_bytes
        captured["filename"] = filename
        return {"text": "  File transcript  "}

    monkeypatch.setattr(transcription, "transcribe_audio", transcribe)

    result = await transcription.transcribe_audio_file(audio_path)

    assert result == "File transcript"
    assert captured == {"audio_bytes": b"audio", "filename": "recording.mp3"}


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (httpx.ConnectError("connection refused"), "local whisper.cpp server is unavailable"),
        (httpx.ReadTimeout("request timed out"), "Transcription timed out"),
    ],
)
async def test_transcription_reports_server_connection_and_timeout_errors(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    message: str,
) -> None:
    async def convert_audio(*args: object, **kwargs: object) -> bytes:
        return b"normalized-wav"

    monkeypatch.setattr(transcription, "_convert_to_whisper_wav", convert_audio)

    def handler(request: httpx.Request) -> httpx.Response:
        raise failure

    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        transcription.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    with pytest.raises(ValueError, match=message):
        await transcription.transcribe_audio(b"source-audio")
