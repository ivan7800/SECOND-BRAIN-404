@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker no esta disponible.
  echo Instala Docker Desktop y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [OK] Creado .env
) else (
  echo [OK] .env ya existe
)

echo.
echo Configuracion inicial terminada.
echo Revisa .env si quieres usar Google Drive.
pause
