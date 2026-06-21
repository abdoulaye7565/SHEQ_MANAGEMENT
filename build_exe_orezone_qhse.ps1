param(
    [switch]$IncludePreparedDatabase
)

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
    param([string]$ModuleName)
    & $VenvPython -c "import $ModuleName" 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Ensure-PythonPackage {
    param([string]$ModuleName, [string]$Requirement)
    if (Test-PythonImport $ModuleName) {
        Write-Ok "$ModuleName deja disponible"
        return
    }
    & $VenvPython -m pip install $Requirement
    if ($LASTEXITCODE -ne 0) { throw "Installation de $Requirement impossible." }
    Write-Ok "$Requirement installe"
}

$ProjectDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython  = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$IconPath    = Join-Path $ProjectDir "assets\orezone_qhse.ico"
$DistDir     = Join-Path $ProjectDir "dist"
$AppDistDir  = Join-Path $DistDir "OREZONE_QHSE"
$ExePath     = Join-Path $AppDistDir "OREZONE_QHSE.exe"
$ReleaseZip  = Join-Path $DistDir "OREZONE_QHSE_INSTALLABLE.zip"

Write-Host "Generation de l'executable OREZONE QHSE" -ForegroundColor Blue
Write-Host "Dossier projet: $ProjectDir"

if (-not (Test-Path $VenvPython)) {
    throw "Environnement .venv introuvable. Lance d'abord install_orezone_qhse.bat."
}

# ── 1. Dependances build ───────────────────────────────────────────────────────
Write-Step "Installation/verification des dependances build"
Ensure-PythonPackage "flet" "flet==0.84.0"
if (Test-Path (Join-Path $ProjectDir "requirements-build.txt")) {
    & $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements-build.txt") --quiet
    if ($LASTEXITCODE -ne 0) { throw "Installation requirements-build.txt impossible." }
} else {
    Ensure-PythonPackage "reportlab" "reportlab==4.4.9"
    Ensure-PythonPackage "PyInstaller" "pyinstaller"
}
Write-Ok "PyInstaller et dependances disponibles"

# ── 2. S'assurer que le binaire Flet est disponible pour le hook ──────────────
Write-Step "Pre-telechargement du binaire Flet desktop (operation unique)"
# The Flet PyInstaller hook reads the binary from the developer's local cache
# (~/.flet/client/...) and bundles it automatically. We must ensure it exists.
$FletCacheScript = @'
import sys
try:
    import flet_desktop
    cache_dir = flet_desktop.ensure_client_cached()
    flet_exe  = cache_dir / "flet" / "flet.exe"
    if flet_exe.is_file():
        print("OK:" + str(cache_dir))
    else:
        print("NOT_FOUND")
except Exception as exc:
    print(f"ERROR:{exc}")
'@
$FletCacheResult = (& $VenvPython -c $FletCacheScript).Trim()
if (-not $FletCacheResult -or $FletCacheResult -like "NOT_FOUND*" -or $FletCacheResult -like "ERROR:*") {
    throw "Impossible de localiser/telecharger le binaire Flet: $FletCacheResult`nVerifie ta connexion internet (telechargement unique ~95 Mo)."
}
Write-Ok "Cache Flet pret: $($FletCacheResult -replace '^OK:','')"

# ── 3. Nettoyage ───────────────────────────────────────────────────────────────
Write-Step "Nettoyage des anciens fichiers de build"
$ProjectRoot = (Resolve-Path $ProjectDir).Path
foreach ($PathToClean in @((Join-Path $ProjectDir "build"), $AppDistDir)) {
    if (Test-Path $PathToClean) {
        $Resolved = (Resolve-Path $PathToClean).Path
        if (-not $Resolved.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Nettoyage refuse hors du dossier projet: $Resolved"
        }
        Remove-Item -Recurse -Force -LiteralPath $Resolved
    }
}
if (Test-Path $ReleaseZip) { Remove-Item -Force -LiteralPath $ReleaseZip }
Write-Ok "Build precedent nettoye"

# ── 4. Compilation PyInstaller ────────────────────────────────────────────────
Write-Step "Compilation de l'application (PyInstaller)"

$addDataSchema       = "$(Join-Path $ProjectDir 'app\db\schema.sql');app\db"
$addDataAssets       = "$(Join-Path $ProjectDir 'assets');assets"
$FletMaterialDir     = Join-Path $ProjectDir ".venv\Lib\site-packages\flet\controls\material"
if (-not (Test-Path $FletMaterialDir)) {
    throw "Ressources Flet introuvables: $FletMaterialDir"
}
$addDataFletMaterial = "$FletMaterialDir;flet\controls\material"

$iconArg = @()
if (Test-Path $IconPath) { $iconArg = @("--icon", $IconPath) }

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

if ($LASTEXITCODE -ne 0) { throw "Compilation PyInstaller echouee." }
if (-not (Test-Path $ExePath))  { throw "Executable non trouve apres compilation: $ExePath" }
Write-Ok "Executable cree: $ExePath"

# ── 5. Verifier que le binaire Flet est bien bundle ───────────────────────────
Write-Step "Verification du bundle Flet offline"
# The Flet PyInstaller hook (hook-flet.py) automatically copies the extracted
# Flet desktop binary into _internal/flet_desktop/app/flet/.
# main.py sets FLET_VIEW_PATH to point there so no download is ever needed.
$FletExeInBundle = Join-Path $AppDistDir "_internal\flet_desktop\app\flet\flet.exe"
if (-not (Test-Path $FletExeInBundle)) {
    throw "flet.exe absent du bundle PyInstaller. Le hook Flet n'a pas fonctionne."
}
$FletBundleSizeMb = [math]::Round(
    (Get-ChildItem (Join-Path $AppDistDir "_internal\flet_desktop\app\flet") -Recurse |
     Measure-Object -Property Length -Sum).Sum / 1MB, 1
)
Write-Ok "Binaire Flet confirme dans le bundle ($($FletBundleSizeMb) Mo)"

# ── 6. Dossiers runtime et fichiers annexes ────────────────────────────────────
Write-Step "Preparation des dossiers et fichiers annexes"
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "data")    | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "exports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "backups") | Out-Null

$PreparedDb = Join-Path $ProjectDir "data\orezone.db"
if ($IncludePreparedDatabase -and (Test-Path $PreparedDb)) {
    Copy-Item $PreparedDb (Join-Path $AppDistDir "data\orezone.db") -Force
    Write-Host "ATTENTION: base de donnees preparee incluse dans le paquet." -ForegroundColor Yellow
} else {
    Write-Ok "Paquet propre: aucune base reelle incluse"
}

$ModelePath = Join-Path $ProjectDir "exports\modele_import_employes_orezone.xlsx"
if (Test-Path $ModelePath) {
    Copy-Item $ModelePath (Join-Path $AppDistDir "exports\modele_import_employes_orezone.xlsx") -Force
}
if (Test-Path (Join-Path $ProjectDir "docs")) {
    Copy-Item (Join-Path $ProjectDir "docs") (Join-Path $AppDistDir "docs") -Recurse -Force
}
foreach ($f in @(
    "installer_orezone_qhse.ps1",
    "installer_orezone_qhse.bat",
    "reinitialiser_base_orezone_qhse.ps1",
    "reinitialiser_base_orezone_qhse.bat"
)) {
    $src = Join-Path $ProjectDir $f
    if (Test-Path $src) { Copy-Item $src (Join-Path $AppDistDir $f) -Force }
}
Write-Ok "Fichiers annexes prets"

# ── 7. Notice d'installation ──────────────────────────────────────────────────
Write-Step "Creation de la notice d'installation"
@"
OREZONE QHSE - Notice d'installation Windows
=============================================

PRE-REQUIS
----------
- Windows 10 ou 11 (64 bits)
- Aucune installation de Python ou autre logiciel requise
- Fonctionne SANS connexion internet

INSTALLATION SUR UN AUTRE ORDINATEUR
--------------------------------------
1. Copier le dossier OREZONE_QHSE sur le PC cible
   (ou decompresser OREZONE_QHSE_INSTALLABLE.zip)
2. Ouvrir le dossier OREZONE_QHSE
3. Double-cliquer sur  installer_orezone_qhse.bat
4. Cliquer "Oui" si Windows demande une autorisation
5. Un raccourci est cree sur le Bureau et dans le menu Demarrer

LANCEMENT PORTABLE (sans installation)
---------------------------------------
Double-cliquer directement sur OREZONE_QHSE.exe depuis ce dossier.
La base sera creee dans : %APPDATA%\OREZONE_QHSE\data\orezone.db

DONNEES ET EXPORTS
------------------
- Base de donnees : %APPDATA%\OREZONE_QHSE\data\orezone.db
- Exports Excel   : Documents\OREZONE_QHSE\exports
- Lors d'une mise a jour, la base existante est conservee

MISE A JOUR
-----------
Relancer installer_orezone_qhse.bat avec la nouvelle version.
La base de donnees est automatiquement preservee.

PROBLEMES COURANTS
------------------
- Windows Defender bloque l'exe : cliquer "Informations complementaires"
  puis "Executer quand meme" (l'exe n'est pas signe numeriquement)
- Ecran noir au lancement : attendre 5-10 secondes (premier lancement)
- Pour reinitialiser la base : lancer reinitialiser_base_orezone_qhse.bat

CONTENU DU PAQUET
-----------------
  OREZONE_QHSE.exe       -> Application principale
  flet_view/             -> Moteur graphique Flutter (offline, inclus)
  _internal/             -> Bibliotheques Python (ne pas supprimer)
  assets/                -> Icones et ressources visuelles
  data/                  -> Base de donnees SQLite (creee au 1er lancement)
  exports/               -> Modele import employes
  installer_*.bat/.ps1   -> Installateur Windows
  reinitialiser_*.bat    -> Reinitialisation base de donnees
"@ | Set-Content -Path (Join-Path $AppDistDir "LIRE_AVANT_INSTALLATION.txt") -Encoding UTF8
Write-Ok "Notice creee"

# ── 8. Raccourci local ────────────────────────────────────────────────────────
$ShortcutPath = Join-Path $AppDistDir "OREZONE QHSE.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $AppDistDir
$Shortcut.Description = "Lancer OREZONE QHSE"
if (Test-Path $IconPath) { $Shortcut.IconLocation = "$IconPath,0" }
$Shortcut.Save()
Write-Ok "Raccourci cree dans le dossier de distribution"

# ── 9. Archive ZIP installable ────────────────────────────────────────────────
Write-Step "Creation de l'archive installable"
$ArchiveCreated = $false
for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    try {
        Start-Sleep -Seconds 2
        Compress-Archive -Path $AppDistDir -DestinationPath $ReleaseZip -Force
        $ArchiveCreated = $true
        break
    } catch {
        if ($Attempt -eq 5) { throw }
        Write-Host "Archive occupee, nouvelle tentative $($Attempt+1)/5..." -ForegroundColor Yellow
    }
}
if (-not $ArchiveCreated) {
    Write-Host "Compress-Archive indisponible, utilisation de tar.exe..." -ForegroundColor Yellow
    if (Test-Path $ReleaseZip) { Remove-Item -Force -LiteralPath $ReleaseZip }
    & tar.exe -a -c -f $ReleaseZip -C $DistDir "OREZONE_QHSE"
    if ($LASTEXITCODE -ne 0) { throw "Creation de l'archive impossible." }
}
$ZipSizeMb = [math]::Round((Get-Item $ReleaseZip).Length / 1MB, 1)
Write-Ok "Archive creee ($($ZipSizeMb) Mo): $ReleaseZip"

# ── Recapitulatif ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Generation terminee avec succes." -ForegroundColor Green
Write-Host ""
Write-Host "Pour distribuer sur un autre PC sans internet :" -ForegroundColor Yellow
Write-Host "  -> Envoyer : $ReleaseZip" -ForegroundColor White
Write-Host "  -> Sur le PC cible : decompresser, puis lancer installer_orezone_qhse.bat" -ForegroundColor White
Write-Host ""
Write-Host "Mode portable (sans installation) :" -ForegroundColor Yellow
Write-Host "  -> Copier le dossier $AppDistDir et lancer OREZONE_QHSE.exe" -ForegroundColor White
