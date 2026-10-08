#!/usr/bin/env bash
set -e
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m nano.cli init
printf '\nNano AI ready. Start local llama.cpp server with: python -m nano.cli llama\nThen in another terminal: python -m nano.cli web\n'
