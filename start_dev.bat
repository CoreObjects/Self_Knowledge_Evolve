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

set "RELOAD=%UVICORN_RELOAD%"
if "%RELOAD%"=="" set "RELOAD=1"

set "PYTHONUNBUFFERED=1"

if "%RELOAD%"=="1" (
  "%PYTHON%" -m uvicorn run_dev:app --host %HOST% --port %PORT% --reload %*
) else (
  "%PYTHON%" -m uvicorn run_dev:app --host %HOST% --port %PORT% %*
)

endlocal
