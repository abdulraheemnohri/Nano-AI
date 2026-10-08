# Nano AI

Nano AI is a lightweight, privacy-first local talking assistant built around **Qwen3 1.7B**.

## Quick installation

### Linux

````
git clone https://github.com/abdulraheemnohri/Nano-AI.git
cd Nano-AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
nano-ai init
nano-ai download-model
nano-ai llama
````

Open a second terminal:

````
cd Nano-AI
source .venv/bin/activate
nano-ai web
````

Open **http://127.0.0.1:8000**.

### Windows PowerShell

````
git clone https://github.com/abdulraheemnohri/Nano-AI.git
cd Nano-AI
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
nano-ai init
nano-ai download-model
nano-ai llama
````

In another PowerShell window:

````
cd Nano-AI
.\\.venv\\Scripts\\Activate.ps1
nano-ai web
````

## Required runtime

Nano requires Python 3.10+ and a llama.cpp installation containing **llama-server**. Verify with `llama-server --help` (Windows: `llama-server.exe --help`).

Default model: **Qwen3-1.7B-Q4_K_M.gguf**. The model is kept locally under `models/`.

## Voice setup

Voice is optional. Install:

````
pip install -r requirements-voice.txt
````

Configure a local Vosk model at `models/vosk/` and set `NANO_STT_MODEL=models/vosk`. Configure Piper with a local executable and ONNX voice:

Linux:
````
export NANO_STT_MODEL=models/vosk
export NANO_PIPER_COMMAND=piper
export NANO_PIPER_VOICE=models/piper/<voice>.onnx
````

Windows PowerShell:
````
$env:NANO_STT_MODEL="models/vosk"
$env:NANO_PIPER_COMMAND="piper"
$env:NANO_PIPER_VOICE="models/piper/<voice>.onnx"
````

Restart Nano after changing environment variables. Voice flow: **Microphone → local WAV → Vosk → Qwen3 1.7B → Piper → speaker**. WAV upload is available as a fallback.

## Complete UI guide

**Talk:** text chat, conversation switching, new chats, microphone recording, WAV upload and TTS playback.

**Memory:** search durable memories and use **Forget** to remove individual entries.

**Learning:** inspect explicit learning events. Nano does not silently retrain model weights.

**Skills:** enable or disable reusable prompt skills.

**Knowledge:** paste local notes/documentation and choose **Import locally** to make them searchable.

**Model:** inspect model/runtime information.

**Settings:** change supported Nano preferences such as language, voice, learning, theme and temperature.

**System:** inspect runtime and voice readiness.

## Learning examples

````
Remember that I prefer Urdu.
My name is Abdul.
I like concise answers.
Learn that I prefer Roman Urdu.
````

Learning is intentionally explicit and user-visible. Imported knowledge is stored as local searchable memory.

## CLI

````
nano-ai --help
nano-ai init
nano-ai status
nano-ai model
nano-ai download-model
nano-ai llama
nano-ai web
````

## Configuration

Important variables: `NANO_HOST`, `NANO_PORT`, `NANO_LLAMA_URL`, `NANO_MODEL_NAME`, `NANO_MAX_CONTEXT`, `NANO_TEMPERATURE`, `NANO_STT_MODEL`, `NANO_PIPER_COMMAND`, `NANO_PIPER_VOICE`.

Default database: `data/nano.sqlite3`.

## Troubleshooting

- **llama-server not found:** install llama.cpp and add its binary directory to PATH.
- **Model server offline:** run `nano-ai status` and start `nano-ai llama`.
- **Model missing:** run `nano-ai model` and verify the GGUF exists in `models/`.
- **Vosk unavailable:** install voice dependencies and set `NANO_STT_MODEL` to the extracted model directory.
- **Piper unavailable:** configure `NANO_PIPER_COMMAND` and `NANO_PIPER_VOICE`.
- **Microphone unavailable:** grant browser permission or upload a mono 16-bit PCM WAV.
- **Port conflict:** use `nano-ai web --port 8001` or `nano-ai llama --port 8081` and update `NANO_LLAMA_URL` accordingly.

## Security

Nano is local-first and does not require Firebase or a cloud AI provider. It intentionally has no terminal executor, browser automation, device-control agent or arbitrary external plugin execution. Do not expose the local ports publicly without your own authentication/network controls.

## Tests

````
python -m pytest
````

See `docs/INSTALL.md` and `docs/USER_GUIDE.md` for the full guides.