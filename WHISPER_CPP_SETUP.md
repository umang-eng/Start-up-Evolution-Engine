# Local speech-to-text with whisper.cpp

The meetings audio-upload endpoint now sends recordings to a local `whisper.cpp`
HTTP server. The backend uses FFmpeg to normalize each uploaded file to mono,
16 kHz, signed 16-bit PCM WAV before posting it to `/inference`.

## 1. Install build and conversion tools

On macOS with Homebrew:

```bash
xcode-select --install
brew install cmake ffmpeg
```

On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake ffmpeg
```

## 2. Clone, compile, and download the model

```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build --target whisper-server --config Release --parallel
sh ./models/download-ggml-model.sh base
```

The requested `make server` target is not present in the current upstream
`master` Makefile. On older revisions whose Makefile defines it, the legacy
build command is:

```bash
make server
```

For a fresh clone of current upstream, use the CMake commands above; they build
the same built-in HTTP server. The `ggerganov` GitHub URL redirects to the
maintained upstream repository.

## 3. Start the HTTP server on port 8080

For a backend running directly on this computer:

```bash
./build/bin/whisper-server \
  --model models/ggml-base.bin \
  --host 127.0.0.1 \
  --port 8080
```

For the project's Docker Compose API/worker containers, they connect back to the
host using `host.docker.internal`; bind the server to all host interfaces:

```bash
./build/bin/whisper-server \
  --model models/ggml-base.bin \
  --host 0.0.0.0 \
  --port 8080
```

The whisper.cpp example server has no authentication. Do not expose port 8080 to
untrusted networks or the public internet; use a firewall and keep it on a
trusted development network.

## 4. Configure and run this application

For a locally running FastAPI backend, set these values in the repository's
`.env` file (the defaults already match):

```dotenv
WHISPER_HOST=http://localhost:8080
WHISPER_TIMEOUT_SECONDS=180
FFMPEG_BINARY=ffmpeg
```

The Docker Compose API and worker services are configured to use
`http://host.docker.internal:8080`; FFmpeg is installed in the backend runtime
image. Start the speech server in one terminal, then start the application in a
second terminal:

```bash
npm run dev
```

## 5. Verify the server manually

The HTTP endpoint accepts multipart form data and returns JSON:

```bash
curl --fail-with-body http://127.0.0.1:8080/inference \
  -F 'file=@/absolute/path/to/audio.wav' \
  -F 'response_format=json'
```

The supplied WAV should be mono, 16 kHz, and 16-bit PCM. The application itself
accepts browser recordings (for example WebM/Opus) and common audio uploads
(MP3, M4A, WAV, OGG, and FLAC); FFmpeg performs the conversion automatically.

## Backend implementation

`backend/services/transcription.py` contains the complete asynchronous
integration:

- `_convert_to_whisper_wav` writes an isolated temporary input file and invokes
  FFmpeg with `-ac 1 -ar 16000 -c:a pcm_s16le`.
- `transcribe_audio` submits the converted bytes as multipart field `file` to
  `WHISPER_HOST + /inference`, requests `response_format=json`, and maps the
  response into the meeting API's transcript shape.
- `transcribe_audio_file(file_path)` is the file-path helper: it reads the file
  asynchronously and returns the transcribed text.
- Network timeouts, refused connections, HTTP errors, malformed responses,
  missing FFmpeg, and invalid audio are converted to actionable errors for the
  API response.

The authenticated route is
`POST /api/v1/meetings/{meeting_id}/transcript/audio`. It saves the resulting
transcript and marks the meeting as transcribed after successful inference.
