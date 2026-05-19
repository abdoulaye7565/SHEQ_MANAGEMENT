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
$IconPath = Join-Path $ProjectDir "assets\orezone_qhse.ico"
$DistDir = Join-Path $ProjectDir "dist"
$AppDistDir = Join-Path $DistDir "OREZONE_QHSE"
$ExePath = Join-Path $AppDistDir "OREZONE_QHSE.exe"

Write-Host "Generation de l'executable OREZONE QHSE" -ForegroundColor Blue
Write-Host "Dossier projet: $ProjectDir"

if (-not (Test-Path $VenvPython)) {
    throw "Environnement .venv introuvable. Lance d'abord install_orezone_qhse.bat."
}

Write-Step "Installation/verification de PyInstaller"
& $VenvPython -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) {
    & $VenvPython -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Installation de PyInstaller impossible. Verifie la connexion internet."
    }
}
Write-Ok "PyInstaller disponible"

Write-Step "Nettoyage des anciens fichiers de build"
if (Test-Path (Join-Path $ProjectDir "build")) {
    Remove-Item -Recurse -Force (Join-Path $ProjectDir "build")
}
if (Test-Path $AppDistDir) {
    Remove-Item -Recurse -Force $AppDistDir
}
Write-Ok "Build precedent nettoye"

Write-Step "Compilation de l'application"
$addDataSchema = "app\db\schema.sql;app\db"
$addDataAssets = "assets;assets"
$iconArg = @()
if (Test-Path $IconPath) {
    $iconArg = @("--icon", $IconPath)
}

& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "OREZONE_QHSE" `
    --distpath "$DistDir" `
    --workpath "$ProjectDir\build" `
    --specpath "$ProjectDir\build" `
    --add-data "$addDataSchema" `
    --add-data "$addDataAssets" `
    @iconArg `
    "main.py"

if ($LASTEXITCODE -ne 0) {
    throw "Compilation PyInstaller echouee."
}

if (-not (Test-Path $ExePath)) {
    throw "Executable non trouve apres compilation: $ExePath"
}
Write-Ok "Executable cree: $ExePath"

Write-Step "Preparation des dossiers runtime"
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "exports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "backups") | Out-Null

if (Test-Path (Join-Path $ProjectDir "data\orezone.db")) {
    Copy-Item (Join-Path $ProjectDir "data\orezone.db") (Join-Path $AppDistDir "data\orezone.db") -Force
}

if (Test-Path (Join-Path $ProjectDir "exports\modele_import_employes_orezone.xlsx")) {
    Copy-Item (Join-Path $ProjectDir "exports\modele_import_employes_orezone.xlsx") (Join-Path $AppDistDir "exports\modele_import_employes_orezone.xlsx") -Force
}

if (Test-Path (Join-Path $ProjectDir "docs")) {
    Copy-Item (Join-Path $ProjectDir "docs") (Join-Path $AppDistDir "docs") -Recurse -Force
}

foreach ($installerFile in @(
    "installer_orezone_qhse.ps1",
    "installer_orezone_qhse.bat"
)) {
    $source = Join-Path $ProjectDir $installerFile
    if (Test-Path $source) {
        Copy-Item $source (Join-Path $AppDistDir $installerFile) -Force
    }
}

Write-Ok "Dossiers runtime prepares"

Write-Step "Creation d'un raccourci local dans le dossier dist"
$ShortcutPath = Join-Path $AppDistDir "OREZONE QHSE.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $AppDistDir
$Shortcut.Description = "Lancer OREZONE QHSE"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()
Write-Ok "Raccourci cree dans le dossier de distribution"

Write-Host ""
Write-Host "Generation terminee." -ForegroundColor Green
Write-Host "Dossier a copier sur une autre machine:" -ForegroundColor Green
Write-Host $AppDistDir -ForegroundColor Green
Write-Host ""
Write-Host "Sur l'autre machine, lancer:" -ForegroundColor Green
Write-Host "installer_orezone_qhse.bat pour installer, ou OREZONE_QHSE.exe en mode portable" -ForegroundColor Green
