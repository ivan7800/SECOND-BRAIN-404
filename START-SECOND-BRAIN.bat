@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" copy ".env.example" ".env" >nul

docker compose up -d --build
if errorlevel 1 (
  echo [ERROR] No se pudo iniciar Second Brain 404.
  pause
  exit /b 1
)

timeout /t 2 /nobreak >nul
start "" "http://localhost:4040"
