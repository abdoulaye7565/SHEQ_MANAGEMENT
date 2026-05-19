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
$ExePath = Join-Path $InstallRoot "OREZONE_QHSE.exe"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "OREZONE QHSE.lnk"
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\OREZONE QHSE"
$StartMenuShortcut = Join-Path $StartMenuDir "OREZONE QHSE.lnk"
$IconPath = Join-Path $InstallRoot "assets\orezone_qhse.ico"

Write-Host "Installation OREZONE QHSE Desktop" -ForegroundColor Blue
Write-Host "Source: $SourceDir"
Write-Host "Destination: $InstallRoot"

if (-not (Test-Path (Join-Path $SourceDir "OREZONE_QHSE.exe"))) {
    throw "Executable OREZONE_QHSE.exe introuvable dans le dossier installateur."
}

Write-Step "Preparation des donnees existantes"
$TempData = $null
if (Test-Path (Join-Path $InstallRoot "data")) {
    $TempData = Join-Path $env:TEMP ("orezone_qhse_data_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    Copy-Item (Join-Path $InstallRoot "data") $TempData -Recurse -Force
    Write-Ok "Donnees existantes preservees"
}
else {
    Write-Ok "Nouvelle installation"
}

Write-Step "Copie de l'application"
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Get-ChildItem -LiteralPath $InstallRoot -Force |
    Where-Object { $_.Name -notin @("data", "exports", "backups") } |
    Remove-Item -Recurse -Force
Copy-Item (Join-Path $SourceDir "*") $InstallRoot -Recurse -Force
if ($TempData) {
    Remove-Item (Join-Path $InstallRoot "data") -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item $TempData (Join-Path $InstallRoot "data") -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "exports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "backups") | Out-Null
Write-Ok "Application installee"

Write-Step "Creation des raccourcis"
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
$Shell = New-Object -ComObject WScript.Shell
foreach ($ShortcutPath in @($DesktopShortcut, $StartMenuShortcut)) {
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = $InstallRoot
    $Shortcut.Description = "Lancer OREZONE QHSE"
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = "$IconPath,0"
    }
    $Shortcut.Save()
}
Write-Ok "Raccourcis crees"

Write-Host ""
Write-Host "Installation terminee. Lance OREZONE QHSE depuis le Bureau ou le menu Demarrer." -ForegroundColor Green
