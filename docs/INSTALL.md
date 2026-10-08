# Nano AI — Complete Installation Guide

## 1. Prerequisites

Linux or Windows is supported. Install Python 3.10+, Git, and llama.cpp with `llama-server`.

Verify Linux:
````
python3 --version
git --version
llama-server --help
````

Verify Windows PowerShell:
````
py --version
git --version
llama-server.exe --help
````

## 2. Clone

````
git clone https://github.com/abdulraheemnohri/Nano-AI.git
cd Nano-AI
````

## 3. Create Python environment

Linux:
````
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
````

Windows PowerShell:
````
py -3 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
````

## 4. Initialize

````
nano-ai init
nano-ai status
````

## 5. Install Qwen3 1.7B

Nano's default model is `Qwen3-1.7B-Q4_K_M.gguf`. Download it with:

````
nano-ai download-model
````

Or manually place the GGUF at `models/Qwen3-1.7B-Q4_K_M.gguf`.

Check with `nano-ai model`.

## 6. Start inference

Terminal 1:
````
nano-ai llama
````

The local llama.cpp endpoint defaults to `http://127.0.0.1:8080`. Keep this terminal running.

## 7. Start Nano

Terminal 2, with the virtual environment activated:
````
nano-ai web
````

Open `http://127.0.0.1:8000`.

## 8. Voice installation

Voice is optional:
````
pip install -r requirements-voice.txt
````

Set Vosk:

Linux:
````
export NANO_STT_MODEL=models/vosk
````

PowerShell:
````
$env:NANO_STT_MODEL="models/vosk"
````

Extract a compatible Vosk model under `models/vosk/`.

Set Piper:

Linux:
````
export NANO_PIPER_COMMAND=piper
export NANO_PIPER_VOICE=models/piper/<voice>.onnx
````

PowerShell:
````
$env:NANO_PIPER_COMMAND="piper"
$env:NANO_PIPER_VOICE="models/piper/<voice>.onnx"
````

Restart Nano after changing environment variables.

## 9. Verify

````
nano-ai status
nano-ai model
python -m pytest
````

Use **System** in the UI to inspect runtime/voice status.

## 10. Data

Default database: `data/nano.sqlite3`. Models are under `models/`. The repository ignores local database/model/audio files.

## 11. Offline operation

After Python packages, Qwen, Vosk and Piper files are installed, inference and voice processing can run locally. Initial downloads require internet unless files are transferred manually.

## 12. Troubleshooting

**llama-server not found:** install llama.cpp and put its binary directory on PATH.

**Local Qwen server is not reachable:** run `nano-ai llama` and keep it running.

**Model missing:** verify `models/Qwen3-1.7B-Q4_K_M.gguf` or run `nano-ai download-model`.

**Vosk model not found:** verify `NANO_STT_MODEL` points to the extracted model directory.

**Piper executable not found:** verify `NANO_PIPER_COMMAND`.

**Microphone unavailable:** grant browser microphone permission or upload a mono 16-bit PCM WAV.

**Port conflict:** use `nano-ai web --port 8001` or `nano-ai llama --port 8081`; if changing llama port, set `NANO_LLAMA_URL=http://127.0.0.1:8081`.
