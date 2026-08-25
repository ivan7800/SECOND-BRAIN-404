@echo off
setlocal
cd /d "%~dp0"
docker compose -f docker-compose.yml -f docker-compose.ollama.yml down
docker compose down
echo [OK] Servicios detenidos.
pause
