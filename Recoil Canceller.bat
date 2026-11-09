@echo off
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo Install failed. Is Python installed and on PATH?
  pause
  exit /b 1
)
where pythonw >nul 2>&1
if not errorlevel 1 (
  start "" pythonw recoil_canceller.py
  exit /b 0
)
start "" python recoil_canceller.py
