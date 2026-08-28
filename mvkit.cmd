@echo off
rem MusicVideoKit on Windows - the pipeline runs inside the Docker container.
rem   mvkit.cmd doctor
rem   mvkit.cmd new mysong C:\music\song.mp3
rem   mvkit.cmd transcribe mysong
rem   mvkit.cmd beats mysong
rem Without Docker: install Git Bash + ffmpeg + whisper.cpp and use .\mvkit
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker not found. Install Docker Desktop: https://docs.docker.com/desktop/
  echo Or use Git Bash / WSL with ffmpeg + whisper.cpp and run  .\mvkit
  exit /b 1
)

set "DC=docker compose"
docker compose version >nul 2>&1 || set "DC=docker-compose"

if "%MVKIT_MODELS%"=="" (
  if exist "%USERPROFILE%\.cache\whisper" (
    set "MVKIT_MODELS=%USERPROFILE%\.cache\whisper"
  ) else (
    if not exist ".cache\whisper" mkdir ".cache\whisper"
    set "MVKIT_MODELS=./.cache/whisper"
  )
)

if "%~1"=="" (
  %DC% run --rm mvkit bash ./mvkit --native help
  exit /b %errorlevel%
)

%DC% run --rm mvkit bash ./mvkit --native %*
exit /b %errorlevel%
