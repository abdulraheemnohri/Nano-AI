# Installation

Requirements: Python 3.10+ and a local llama.cpp build exposing llama-server.

Linux/Windows:
1. Create a virtual environment.
2. Run pip install -e .
3. Run nano-ai init.
4. Put Qwen3-1.7B-Q4_K_M.gguf in models/ or run nano-ai download-model.
5. Run nano-ai llama.
6. In another terminal run nano-ai web.
7. Open http://127.0.0.1:8000.

Optional voice: pip install -e ".[voice]" and configure local Vosk and Piper models.
