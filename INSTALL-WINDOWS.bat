@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  SECOND BRAIN 404 v2.3.0 - INSTALL WINDOWS
echo ============================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker no esta instalado o no esta en PATH.
  echo Instala Docker Desktop y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker Desktop no esta iniciado.
  echo Inicia Docker Desktop y espera a que el motor este listo.
  pause
  exit /b 1
)

if not exist ".env.example" (
  echo [ERROR] Falta .env.example. El paquete esta incompleto.
  pause
  exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul

echo [1/4] Validando Docker Compose...
docker compose config -q
if errorlevel 1 goto :fail

echo [2/4] Construyendo aplicacion...
docker compose build
if errorlevel 1 goto :fail

echo [3/4] Iniciando Second Brain...
docker compose up -d
if errorlevel 1 goto :fail

echo [4/4] Esperando API...
for /L %%i in (1,1,30) do (
  powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://localhost:4040/api/health' -TimeoutSec 2; if($r.version -like '2.3.*'){ exit 0 } else { exit 2 } } catch { exit 1 }"
  if not errorlevel 1 goto :ready
  timeout /t 2 /nobreak >nul
)

echo [ERROR] La API v2.3 no respondio a tiempo.
goto :fail

:ready
echo.
echo [OK] Instalacion base completada.
echo Abriendo http://localhost:4040
start "" "http://localhost:4040"
echo.
echo Para IA local ejecuta:
echo   START-LOCAL-AI.bat
echo y despues:
echo   INSTALL-LOCAL-MODELS.bat
echo.
echo Para medir la calidad del retrieval:
echo   RUN-RAG-BENCHMARK.bat
pause
exit /b 0

:fail
echo.
echo [ERROR] La instalacion no se pudo completar.
echo Ejecutando diagnostico...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0WINDOWS-DIAGNOSTIC.ps1"
pause
exit /b 1
