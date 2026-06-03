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

function Test-PythonImport {
    param(
        [string]$ModuleName
    )
    & $VenvPython -c "import $ModuleName" | Out-Null
    return $LASTEXITCODE -eq 0
}

function Ensure-PythonPackage {
    param(
        [string]$ModuleName,
        [string]$Requirement
    )
    if (Test-PythonImport $ModuleName) {
        Write-Ok "$ModuleName deja disponible"
        return
    }
    & $VenvPython -m pip install $Requirement
    if ($LASTEXITCODE -ne 0) {
        throw "Installation de $Requirement impossible."
    }
    Write-Ok "$Requirement installe"
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$IconPath = Join-Path $ProjectDir "assets\orezone_qhse.ico"
$DistDir = Join-Path $ProjectDir "dist"
$AppDistDir = Join-Path $DistDir "OREZONE_QHSE"
$ExePath = Join-Path $AppDistDir "OREZONE_QHSE.exe"
$ReleaseZip = Join-Path $DistDir "OREZONE_QHSE_INSTALLABLE.zip"

Write-Host "Generation de l'executable OREZONE QHSE" -ForegroundColor Blue
Write-Host "Dossier projet: $ProjectDir"

if (-not (Test-Path $VenvPython)) {
    throw "Environnement .venv introuvable. Lance d'abord install_orezone_qhse.bat."
}

Write-Step "Installation/verification de PyInstaller"
Ensure-PythonPackage "flet" "flet==0.84.0"
if (Test-Path (Join-Path $ProjectDir "requirements-build.txt")) {
    & $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements-build.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Installation requirements-build.txt impossible."
    }
}
else {
    Ensure-PythonPackage "reportlab" "reportlab==4.4.9"
    Ensure-PythonPackage "PyInstaller" "pyinstaller"
}
Write-Ok "PyInstaller disponible"

Write-Step "Nettoyage des anciens fichiers de build"
$BuildDir = Join-Path $ProjectDir "build"
$ProjectRoot = (Resolve-Path $ProjectDir).Path
foreach ($PathToClean in @($BuildDir, $AppDistDir)) {
    if (Test-Path $PathToClean) {
        $ResolvedPath = (Resolve-Path $PathToClean).Path
        if (-not $ResolvedPath.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Nettoyage refuse hors du dossier projet: $ResolvedPath"
        }
        Remove-Item -Recurse -Force -LiteralPath $ResolvedPath
    }
}
if (Test-Path $ReleaseZip) {
    Remove-Item -Force -LiteralPath $ReleaseZip
}
Write-Ok "Build precedent nettoye"

Write-Step "Compilation de l'application"
$addDataSchema = "$(Join-Path $ProjectDir 'app\db\schema.sql');app\db"
$addDataAssets = "$(Join-Path $ProjectDir 'assets');assets"
$FletMaterialDir = Join-Path $ProjectDir ".venv\Lib\site-packages\flet\controls\material"
if (-not (Test-Path $FletMaterialDir)) {
    throw "Ressources Flet introuvables: $FletMaterialDir"
}
$addDataFletMaterial = "$FletMaterialDir;flet\controls\material"
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
    --add-data "$addDataFletMaterial" `
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

$PreparedDatabase = Join-Path $ProjectDir "data\orezone.db"
if (Test-Path $PreparedDatabase) {
    Copy-Item $PreparedDatabase (Join-Path $AppDistDir "data\orezone.db") -Force
}

if (Test-Path (Join-Path $ProjectDir "exports\modele_import_employes_orezone.xlsx")) {
    Copy-Item (Join-Path $ProjectDir "exports\modele_import_employes_orezone.xlsx") (Join-Path $AppDistDir "exports\modele_import_employes_orezone.xlsx") -Force
}

if (Test-Path (Join-Path $ProjectDir "docs")) {
    Copy-Item (Join-Path $ProjectDir "docs") (Join-Path $AppDistDir "docs") -Recurse -Force
}

foreach ($installerFile in @(
    "installer_orezone_qhse.ps1",
    "installer_orezone_qhse.bat",
    "reinitialiser_base_orezone_qhse.ps1",
    "reinitialiser_base_orezone_qhse.bat"
)) {
    $source = Join-Path $ProjectDir $installerFile
    if (Test-Path $source) {
        Copy-Item $source (Join-Path $AppDistDir $installerFile) -Force
    }
}

Write-Ok "Dossiers runtime prepares"

Write-Step "Creation de la notice d'installation"
$ReadmePath = Join-Path $AppDistDir "LIRE_AVANT_INSTALLATION.txt"
@"
OREZONE QHSE - Installation Windows

1. Copier le dossier OREZONE_QHSE sur le PC cible ou decompresser OREZONE_QHSE_INSTALLABLE.zip.
2. Double-cliquer sur installer_orezone_qhse.bat.
3. L'installation copie l'application dans:
   %LOCALAPPDATA%\Programs\OREZONE_QHSE
4. Un raccourci "OREZONE QHSE" est cree sur le Bureau et dans le menu Demarrer.

Donnees:
- La base SQLite est creee automatiquement au premier lancement.
- Lors d'une mise a jour, les dossiers data, exports et backups deja installes sont conserves.
- En version installee, les exports Excel sont crees dans:
  Documents\OREZONE_QHSE\exports
- Pour remplacer une ancienne base par la base prechargee du paquet, lancer reinitialiser_base_orezone_qhse.bat.
  Une sauvegarde est creee avant remplacement dans le dossier backups.
- Pour sauvegarder avant une mise a jour, copier le dossier:
  %LOCALAPPDATA%\Programs\OREZONE_QHSE\data
- Le module Parametres affiche les chemins runtime, la base active et le dossier exports.

Lancement portable:
- Il est aussi possible de lancer directement OREZONE_QHSE.exe depuis ce dossier.
"@ | Set-Content -Path $ReadmePath -Encoding UTF8
Write-Ok "Notice creee"

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

Write-Step "Creation de l'archive installable"
$ArchiveCreated = $false
for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    try {
        Start-Sleep -Seconds 2
        Compress-Archive -Path $AppDistDir -DestinationPath $ReleaseZip -Force
        $ArchiveCreated = $true
        break
    }
    catch {
        if ($Attempt -eq 5) {
            throw
        }
        Write-Host "Archive occupee, nouvelle tentative $($Attempt + 1)/5..." -ForegroundColor Yellow
    }
}
if (-not $ArchiveCreated) {
    throw "Creation de l'archive impossible."
}
Write-Ok "Archive creee: $ReleaseZip"

Write-Host ""
Write-Host "Generation terminee." -ForegroundColor Green
Write-Host "Dossier a copier sur une autre machine:" -ForegroundColor Green
Write-Host $AppDistDir -ForegroundColor Green
Write-Host "Archive installable:" -ForegroundColor Green
Write-Host $ReleaseZip -ForegroundColor Green
Write-Host ""
Write-Host "Sur l'autre machine, lancer:" -ForegroundColor Green
Write-Host "installer_orezone_qhse.bat pour installer, ou OREZONE_QHSE.exe en mode portable" -ForegroundColor Green
