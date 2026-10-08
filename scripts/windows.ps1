$ErrorActionPreference='Stop'
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -e .
.\.venv\Scripts\python.exe -m pip install -U litert-lm
.\.venv\Scripts\python.exe -m nano.cli init
Write-Host 'Nano AI ready.'
Write-Host 'Import: .\.venv\Scripts\nano-ai.exe download-model'
Write-Host 'Terminal 1: .\.venv\Scripts\nano-ai.exe litert-lm'
Write-Host 'Terminal 2: .\.venv\Scripts\nano-ai.exe web'
