param([switch]$Stop)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$newsState = Join-Path $PSScriptRoot '.env.ollama-bridge-state.json'
$newsConfig = Join-Path $PSScriptRoot '.env.ollama-tunnel'
$newsPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$newsLogs = Join-Path $env:TEMP 'librenews-ollama-bridge'

if (Test-Path -LiteralPath $newsState) {
    $newsPrevious = Get-Content -LiteralPath $newsState -Raw | ConvertFrom-Json
    foreach ($newsEntry in $newsPrevious.processes) {
        $newsRunning = Get-Process -Id $newsEntry.id -ErrorAction SilentlyContinue
        if ($newsRunning -and $newsRunning.StartTime.ToUniversalTime().Ticks -eq ([DateTimeOffset]$newsEntry.started).UtcDateTime.Ticks) {
            if (-not $Stop) { throw 'El puente ya está activo. Usar -Stop antes de reiniciarlo.' }
            Stop-Process -Id $newsEntry.id
            Wait-Process -Id $newsEntry.id -Timeout 5 -ErrorAction SilentlyContinue
        }
    }
}
if ($Stop) { Write-Host 'Puente temporal detenido; no se modificó GitHub.'; return }
if (-not (Test-Path -LiteralPath $newsPython)) { throw 'Falta el entorno .venv del proyecto.' }
$newsCloudflared = (Get-Command cloudflared -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $newsLogs -Force > $null
if (-not (Test-Path -LiteralPath $newsConfig)) {
    & $newsPython -c 'from pathlib import Path; from secrets import token_urlsafe; Path(".env.ollama-tunnel").write_text("OLLAMA_BRIDGE_TOKEN=" + token_urlsafe(40) + "\n", encoding="utf-8")'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el token local.' }
}
$newsStarted = @()
try {
    $newsProxy = Start-Process -FilePath $newsPython -ArgumentList '-m news.ollama_bridge' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $newsLogs 'bridge-out.log') -RedirectStandardError (Join-Path $newsLogs 'bridge-error.log')
    $newsStarted += $newsProxy
    $newsTunnel = Start-Process -FilePath $newsCloudflared -ArgumentList 'tunnel --url http://127.0.0.1:11435 --protocol http2 --no-autoupdate' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $newsLogs 'tunnel-out.log') -RedirectStandardError (Join-Path $newsLogs 'tunnel-error.log')
    $newsStarted += $newsTunnel
    $newsUrl = $null
    for ($newsAttempt = 0; $newsAttempt -lt 25; $newsAttempt++) {
        Start-Sleep -Seconds 2
        if ($newsProxy.HasExited -or $newsTunnel.HasExited) { throw 'Un proceso del puente terminó antes de estar listo; revisar los logs locales.' }
        $newsMatch = [regex]::Match((Get-Content -LiteralPath (Join-Path $newsLogs 'tunnel-error.log') -Raw), 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($newsMatch.Success) { $newsUrl = $newsMatch.Value; break }
    }
    if (-not $newsUrl) { throw 'No se obtuvo la dirección temporal del túnel.' }
    & $newsPython -c 'import sys; from dotenv import set_key; set_key(".env.ollama-tunnel", "OLLAMA_BRIDGE_URL", sys.argv[1], quote_mode="never")' $newsUrl
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo guardar la dirección local.' }
    @{ url = $newsUrl; processes = @($newsStarted | ForEach-Object { @{ id = $_.Id; started = $_.StartTime.ToUniversalTime().ToString('o') } }) } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $newsState -Encoding utf8
    Write-Host 'Puente temporal iniciado. URL/token guardados en .env.ollama-tunnel, ignorado por Git.'
    Write-Host 'GitHub no fue configurado ni se hizo push. Detener con: .\start-ollama-bridge.ps1 -Stop'
} catch {
    foreach ($newsProcess in $newsStarted) { Stop-Process -Id $newsProcess.Id -ErrorAction SilentlyContinue }
    throw
}
