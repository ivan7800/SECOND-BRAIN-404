@echo off
setlocal
cd /d "%~dp0"

docker inspect second-brain-ollama >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Ejecuta primero START-LOCAL-AI.bat
  pause
  exit /b 1
)

echo Descargando all-minilm...
docker exec second-brain-ollama ollama pull all-minilm
if errorlevel 1 goto :fail

echo Descargando qwen3:4b...
docker exec second-brain-ollama ollama pull qwen3:4b
if errorlevel 1 goto :fail

echo [OK] Modelos instalados.
pause
exit /b 0

:fail
echo [ERROR] Error descargando modelos.
pause
exit /b 1
