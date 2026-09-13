$ErrorActionPreference = "SilentlyContinue"

function Result($Name, $Ok, $Detail) {
    $mark = if ($Ok) { "[OK]" } else { "[FAIL]" }
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("{0} {1,-24} {2}" -f $mark, $Name, $Detail) -ForegroundColor $color
}

Write-Host ""
Write-Host "SECOND BRAIN 404 v2.3.0 - Windows Diagnostic" -ForegroundColor Cyan
Write-Host "------------------------------------------------"

$docker = Get-Command docker -ErrorAction SilentlyContinue
Result "Docker CLI" ($null -ne $docker) $(if($docker){$docker.Source}else{"No encontrado"})

if ($docker) {
    $dv = docker version --format "{{.Server.Version}}" 2>$null
    Result "Docker Engine" ([bool]$dv) $(if($dv){"v$dv"}else{"Docker Desktop no parece iniciado"})

    $compose = docker compose version 2>$null
    Result "Docker Compose" ([bool]$compose) $(if($compose){$compose}else{"No disponible"})

    docker compose config -q 2>$null
    Result "Compose config" ($LASTEXITCODE -eq 0) $(if($LASTEXITCODE -eq 0){"Configuración válida"}else{"Revisa docker-compose.yml/.env"})
}

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
Result "WSL" ($null -ne $wsl) $(if($wsl){"Disponible"}else{"No encontrado"})

$port = Get-NetTCPConnection -LocalPort 4040 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$health = $null
try {
    $health = Invoke-RestMethod "http://localhost:4040/api/health" -TimeoutSec 3
} catch {}

if ($port -and $health -and $health.status -eq "ok") {
    Result "Puerto 4040" $true "Usado correctamente por Second Brain 404 (PID $($port.OwningProcess))"
} elseif ($port) {
    Result "Puerto 4040" $false "Ocupado por otro proceso o servicio no reconocido (PID $($port.OwningProcess))"
} else {
    Result "Puerto 4040" $true "Libre"
}

$drive = Get-PSDrive -Name ($PWD.Path.Substring(0,1)) -ErrorAction SilentlyContinue
if ($drive) {
    $freeGb = [math]::Round($drive.Free / 1GB, 1)
    Result "Espacio libre" ($freeGb -ge 10) "$freeGb GB"
}

if ($health) {
    $versionOk = [string]$health.version -like "2.3.*"
    Result "Second Brain API" $versionOk "v$($health.version)"
    if ($health.rag) {
        Result "RAG pipeline" ([bool]$health.rag.strategy) "$($health.rag.strategy)"
        Result "Chunking" ($health.rag.chunking -eq "structural") "$($health.rag.chunking)"
        Result "Reranker" ([bool]$health.rag.reranker) "$($health.rag.reranker) · peso $($health.rag.rerank_weight)"
    }
} else {
    Result "Second Brain API" $false "No responde (normal si aún no está iniciado)"
}

Write-Host ""
Write-Host "Diagnóstico finalizado." -ForegroundColor Cyan
