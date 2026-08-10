# Épica K (00-research/09-app-nativa-escritorio.md): empaqueta el
# backend FastAPI (backend/desktop_main.py) con PyInstaller y lo copia
# a frontend/src-tauri/binaries/ con el sufijo target-triple que Tauri
# espera para un sidecar ("externalBin" en tauri.conf.json).
#
# USO (antes de `npx tauri build` o `npx tauri dev`):
#   powershell -File scripts/build_desktop_sidecar.ps1
#
# Requiere: backend/.venv con pyinstaller instalado
# (`pip install pyinstaller`, no está en requirements.txt porque solo
# hace falta para empaquetar la app de escritorio, no para Docker/CI).
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$binariesDir = Join-Path $repoRoot "frontend\src-tauri\binaries"

Push-Location $backendDir
try {
    & ".venv\Scripts\pyinstaller.exe" --onefile --name pulse-backend --paths . desktop_main.py
    if ($LASTEXITCODE -ne 0) {
        throw "pyinstaller fallo con exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$rustTriple = (& rustc -vV | Select-String "^host:").ToString().Split(" ")[1]
New-Item -ItemType Directory -Force -Path $binariesDir | Out-Null
Copy-Item -Force `
    (Join-Path $backendDir "dist\pulse-backend.exe") `
    (Join-Path $binariesDir "pulse-backend-$rustTriple.exe")

Write-Host "OK: sidecar copiado a $binariesDir\pulse-backend-$rustTriple.exe"
