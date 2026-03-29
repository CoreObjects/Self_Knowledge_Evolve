@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

set "HOST=%UVICORN_HOST%"
if "%HOST%"=="" set "HOST=127.0.0.1"

set "PORT=%UVICORN_PORT%"
if "%PORT%"=="" set "PORT=8000"

set "WORKERS=%UVICORN_WORKERS%"

if "%WORKERS%"=="" set "WORKERS=1"

set "PYTHONUNBUFFERED=1"

if defined PYTHONPATH (
  set "PYTHONPATH=%SCRIPT_DIR%semcore;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%SCRIPT_DIR%semcore"
)

set "START_WORKER=%START_WORKER%"
if "%START_WORKER%"=="" set "START_WORKER=1"
if "%START_WORKER%"=="1" (
  start "" /b "%PYTHON%" worker.py
)

"%PYTHON%" -m uvicorn src.app:app --host %HOST% --port %PORT% --workers %WORKERS% %*

endlocal
