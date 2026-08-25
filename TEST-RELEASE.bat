@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Validando Compose...
docker compose config -q
if errorlevel 1 goto :fail

echo [2/3] Construyendo...
docker compose build
if errorlevel 1 goto :fail

echo [3/3] Ejecutando tests dentro de imagen...
docker compose run --rm second-brain python -m unittest discover -s tests -v
if errorlevel 1 goto :fail

echo [OK] Release test superado.
pause
exit /b 0

:fail
echo [ERROR] Release test fallido.
pause
exit /b 1
