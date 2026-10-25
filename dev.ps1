param([switch]$RefreshFeeds, [switch]$RefreshBriefing)

$ErrorActionPreference = 'Stop'
$environmentBefore = @{}
foreach ($name in @('POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_PORT', 'POSTGRES_HOST', 'POSTGRES_SSLMODE', 'DJANGO_SETTINGS_MODULE')) {
    $environmentBefore[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}
Push-Location $PSScriptRoot
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Instalá Python 3.13 para ejecutar el sitio.' }
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Instalá Docker Desktop e iniciá su motor.' }
    $dockerCheck = New-Object System.Diagnostics.Process
    $dockerCheck.StartInfo = New-Object System.Diagnostics.ProcessStartInfo -Property @{
        FileName = 'docker'; Arguments = 'info --format "{{.ServerVersion}}"'
        UseShellExecute = $false; CreateNoWindow = $true; RedirectStandardOutput = $true; RedirectStandardError = $true
    }
    [void]$dockerCheck.Start()
    if (-not $dockerCheck.WaitForExit(15000)) { $dockerCheck.Kill(); throw 'Docker no responde. Iniciá o reiniciá Docker Desktop.' }
    if ($dockerCheck.ExitCode -ne 0) { throw 'Iniciá Docker Desktop y volvé a ejecutar .\dev.ps1.' }
    $dockerCheck.Dispose()

    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno con Python 3.13.' }
    }
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $python -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
    if (-not (Test-Path '.env.local')) {
        @'
import secrets
from pathlib import Path
from dotenv import dotenv_values

values = dict(dotenv_values(".env.example"), DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
              POSTGRES_PASSWORD=secrets.token_urlsafe(32), POSTGRES_DB="sitio_noticias_local")
Path(".env.local").write_text("".join(f"{key}={value or ''}\n" for key, value in values.items()), encoding="utf-8")
'@ | & $python -
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear .env.local.' }
    }
    $env:DJANGO_SETTINGS_MODULE = 'config.local_settings'
    & $python manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'Revisá .env.local; la conexión debe apuntar a esta computadora.' }
    docker compose --env-file .env.local --project-name sitio-noticias-local up -d --wait --wait-timeout 60 db
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL local. Revisá Docker y que el puerto 5433 esté libre.' }
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron aplicar las migraciones locales.' }
    & $python -c "import django; django.setup(); from news.models import Article; raise SystemExit(0 if Article.objects.exists() else 1)"
    if ($RefreshFeeds -or $LASTEXITCODE -eq 1) {
        $feedArguments = @('manage.py', 'ingest_feeds')
        if ($RefreshFeeds) { $feedArguments += '--refresh' }
        & $python @feedArguments
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Algunos RSS no respondieron. El sitio se iniciará con los datos disponibles.' }
    }
    & $python -c "import django, os; django.setup(); raise SystemExit(0 if os.environ.get('GEMINI_API_KEY', '').strip() else 1)"
    if ($LASTEXITCODE -eq 0 -or $RefreshBriefing) {
        $briefingArguments = @('manage.py', 'generate_news_briefing')
        if ($RefreshBriefing) { $briefingArguments += '--force' }
        & $python @briefingArguments
        if ($LASTEXITCODE -ne 0) { Write-Warning 'No se pudo actualizar el resumen. El sitio se iniciará igualmente.' }
    } else { Write-Warning 'El resumen requiere GEMINI_API_KEY en .env.local.' }
    Write-Host 'Abrí http://127.0.0.1:8000/ y registrate para elegir tus categorías. Ctrl+C detiene la web; la base conserva los datos.'
    & $python manage.py runserver 127.0.0.1:8000
} finally {
    foreach ($name in $environmentBefore.Keys) {
        if ($null -eq $environmentBefore[$name]) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
        else { Set-Item "Env:$name" $environmentBefore[$name] }
    }
    Pop-Location
}
