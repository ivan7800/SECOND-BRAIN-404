@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo  SECOND BRAIN 404 v2.3 - RAG BENCHMARK
echo ============================================
echo.
powershell -NoProfile -Command "$body='{""top_k"":5}'; try { $r=Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:4040/api/benchmark' -ContentType 'application/json' -Body $body; $r | ConvertTo-Json -Depth 8; if(-not $r.passed){ exit 2 } } catch { Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }"
if errorlevel 2 (
  echo.
  echo [REVIEW] El benchmark no alcanza los umbrales de calidad.
  pause
  exit /b 2
)
if errorlevel 1 (
  echo.
  echo [ERROR] No se pudo ejecutar el benchmark. Comprueba que Second Brain esta iniciado.
  pause
  exit /b 1
)
echo.
echo [OK] Benchmark RAG superado.
pause
