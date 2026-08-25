@echo off
setlocal
cd /d "%~dp0"
docker ps --filter "name=second-brain"
echo.
powershell -NoProfile -Command "try { Invoke-RestMethod 'http://localhost:4040/api/health' | ConvertTo-Json -Depth 5 } catch { Write-Host $_.Exception.Message -ForegroundColor Red }"
pause
