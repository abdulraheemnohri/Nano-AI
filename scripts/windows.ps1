$ErrorActionPreference='Stop'
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe -m nano.cli init
Write-Host 'Nano AI ready.'
Write-Host 'Start llama-server, then run: .\.venv\Scripts\python.exe -m nano.cli web'
