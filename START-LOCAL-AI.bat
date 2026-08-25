@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" copy ".env.example" ".env" >nul

docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d --build
if errorlevel 1 (
  echo [ERROR] No se pudo iniciar el stack local.
  pause
  exit /b 1
)

echo [OK] Second Brain 404 + Ollama iniciados.
echo Si es la primera vez ejecuta INSTALL-LOCAL-MODELS.bat
timeout /t 2 /nobreak >nul
start "" "http://localhost:4040"
