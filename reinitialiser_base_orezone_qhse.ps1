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

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Join-Path $env:LOCALAPPDATA "Programs\OREZONE_QHSE"
$SourceDb = Join-Path $SourceDir "data\orezone.db"
$TargetDataDir = Join-Path $InstallRoot "data"
$TargetDb = Join-Path $TargetDataDir "orezone.db"
$BackupDir = Join-Path $InstallRoot "backups"

Write-Host "Reinitialisation de la base OREZONE QHSE" -ForegroundColor Blue
Write-Host "Source: $SourceDb"
Write-Host "Destination: $TargetDb"

if (-not (Test-Path $SourceDb)) {
    throw "Base prechargee introuvable dans le dossier installateur: $SourceDb"
}

if (-not (Test-Path $InstallRoot)) {
    throw "Application non installee. Lance d'abord installer_orezone_qhse.bat."
}

Write-Step "Preparation de la sauvegarde"
New-Item -ItemType Directory -Force -Path $TargetDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

if (Test-Path $TargetDb) {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupPath = Join-Path $BackupDir "orezone_backup_${Timestamp}_before_reset.db"
    Copy-Item $TargetDb $BackupPath -Force
    Write-Ok "Ancienne base sauvegardee: $BackupPath"
}
else {
    Write-Ok "Aucune ancienne base trouvee"
}

Write-Step "Copie de la base prechargee"
Copy-Item $SourceDb $TargetDb -Force
Write-Ok "Base prechargee installee"

Write-Host ""
Write-Host "Reinitialisation terminee. Tu peux relancer OREZONE QHSE." -ForegroundColor Green
