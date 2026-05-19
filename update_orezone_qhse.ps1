$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "OK  $Message" -ForegroundColor Green
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$BackupDir = Join-Path $ProjectDir "backups"
$DatabasePath = Join-Path $ProjectDir "data\orezone.db"

Write-Host "Mise a jour OREZONE QHSE" -ForegroundColor Blue
Write-Host "Dossier application: $ProjectDir"

if (-not (Test-Path $VenvPython)) {
    throw "Environnement .venv introuvable. Lance d'abord install_orezone_qhse.bat."
}

Write-Step "Sauvegarde de la base existante"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
if (Test-Path $DatabasePath) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item $DatabasePath (Join-Path $BackupDir "orezone_before_update_$timestamp.db") -Force
    Write-Ok "Base sauvegardee"
}
else {
    Write-Ok "Aucune base existante a sauvegarder"
}

Write-Step "Mise a jour des bibliotheques Python"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Mise a jour pip impossible." }
& $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements.txt") --upgrade
if ($LASTEXITCODE -ne 0) { throw "Mise a jour requirements.txt impossible." }
if (Test-Path (Join-Path $ProjectDir "requirements-reports.txt")) {
    & $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements-reports.txt") --upgrade
    if ($LASTEXITCODE -ne 0) { throw "Mise a jour requirements-reports.txt impossible." }
}
Write-Ok "Bibliotheques a jour"

Write-Step "Migration/verification SQLite"
& $VenvPython -c "from app.db.connection import initialize_database; initialize_database(); print('Database ready')"
if ($LASTEXITCODE -ne 0) { throw "Migration SQLite impossible." }
Write-Ok "Base prete"

Write-Step "Verification technique"
& $VenvPython -m compileall "app" "tests" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Verification technique impossible." }
Write-Ok "Application verifiee"

Write-Host ""
Write-Host "Mise a jour terminee avec succes." -ForegroundColor Green
