#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
python -m pip install -U litert-lm
nano-ai init
printf '\nNano AI ready.\nImport: nano-ai download-model\nTerminal 1: nano-ai litert-lm\nTerminal 2: nano-ai web\n'
