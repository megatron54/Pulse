<#
.SYNOPSIS
    Arranca el stack completo de Pulse (Postgres + backend + frontend +
    scheduler nocturno de Garmin) con un solo comando y abre el
    dashboard en el navegador.

.DESCRIPTION
    Envuelve `docker compose up -d --build` (ver docker-compose.yml en
    la raíz) - deliberadamente NO se reimplementa nada de la lógica de
    arranque en este script (ver decisión explícita del usuario de
    preferir un wrapper simple sobre construir un lanzador dedicado en
    Rust/otro lenguaje: para un proyecto personal de un solo usuario,
    un `.ps1` fino que delega en Docker Compose es suficiente y no
    añade una superficie de mantenimiento nueva).

    Espera a que los 4 servicios queden "healthy" (con un límite de
    tiempo, nunca un bucle infinito) antes de abrir el navegador, para
    no abrir una pestaña contra un backend que todavía no responde.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -NoBrowser
#>
[CmdletBinding()]
param(
    # No abrir el navegador automáticamente al terminar.
    [switch]$NoBrowser,

    # Segundos máximos a esperar a que los servicios queden "healthy"
    # antes de rendirse y avisar (nunca espera indefinidamente).
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".env")) {
    # NUNCA copiar .env.example automaticamente aqui: su POSTGRES_PASSWORD
    # es un placeholder ("cambia-esto-por-una-contrasena-real"), distinto
    # de la contrasena por defecto real usada la primera vez que se creo
    # el volumen de Postgres (docker-compose.yml: pulse_dev_password).
    # Hallazgo real de esta sesion: escribir un .env con ese placeholder
    # rompio silenciosamente el acceso a un volumen YA inicializado -
    # Postgres solo fija la contrasena en el primer arranque (initdb), asi
    # que cualquier cambio posterior de POSTGRES_PASSWORD en .env deja al
    # backend/scheduler sin poder autenticar contra los datos reales que
    # ya existian. Mejor avisar y dejar que el usuario decida a mano.
    Write-Warning "No existe .env - docker-compose.yml usara sus valores por defecto de desarrollo (ver .env.example para la lista completa). Si ya tienes un volumen de Postgres inicializado con otra contrasena, NO copies .env.example sin ajustar POSTGRES_PASSWORD al valor real."
}

Write-Host "Levantando el stack de Pulse (docker compose up -d --build)..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Warning "docker compose up fallo (exit code $LASTEXITCODE). Revisa los logs de arriba - Docker Desktop corriendo? Puerto 3000/8000/5433 libre?"
    exit $LASTEXITCODE
}

# Numero de servicios que debe tener el stack (db, backend, frontend,
# scheduler - ver docker-compose.yml). Se usa mas abajo para no dar por
# "healthy" un arranque a medias donde `docker compose ps` todavia no
# lista todos los servicios (hallazgo de @code-reviewer: justo tras el
# `up -d`, puede haber una ventana breve en la que solo aparezcan 1-2).
$serviciosEsperados = @(docker compose config --services 2>$null).Count

Write-Host "Esperando a que los $serviciosEsperados servicios queden listos (maximo $TimeoutSeconds s)..." -ForegroundColor Cyan
$elapsed = 0
$pollInterval = 3
$allHealthy = $false

while ($elapsed -lt $TimeoutSeconds) {
    # Compose v2 emite JSONL (un objeto JSON por linea) con `--format
    # json`, no un array - de ahi el ForEach-Object por linea. Se
    # envuelve en @(...) porque con UN solo servicio devuelto,
    # PowerShell 5.1 entrega un objeto escalar (no un array), y
    # `.Count` sobre un escalar puede no comportarse como se espera
    # (hallazgo de @code-reviewer).
    $statuses = @(docker compose ps --format json 2>$null | ForEach-Object { $_ | ConvertFrom-Json })

    if ($statuses.Count -eq $serviciosEsperados) {
        # Un servicio "listo" es: si tiene healthcheck definido, que
        # este en "healthy"; si NO tiene healthcheck (Health vacio),
        # que al menos este "running" (nunca se puede asumir listo
        # solo por aparecer en la lista - hallazgo de @code-reviewer,
        # antes esto se colaba como falso positivo).
        $noListos = $statuses | Where-Object {
            ($_.Health -and $_.Health -ne "healthy") -or
            (-not $_.Health -and $_.State -ne "running")
        }
        if (-not $noListos) {
            $allHealthy = $true
            break
        }
    }
    Start-Sleep -Seconds $pollInterval
    $elapsed += $pollInterval
}

if ($allHealthy) {
    Write-Host "Los $serviciosEsperados servicios estan arriba y listos." -ForegroundColor Green
} else {
    Write-Warning "Timeout esperando que los servicios queden listos tras $TimeoutSeconds s - revisa 'docker compose ps' y 'docker compose logs' a mano. Puede que solo necesiten unos segundos mas (el frontend/backend tardan mas en el primer arranque tras un build)."
}

docker compose ps

if (-not $NoBrowser) {
    Write-Host "Abriendo http://localhost:3000 ..." -ForegroundColor Cyan
    Start-Process "http://localhost:3000"
}
