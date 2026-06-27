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

$ProjectDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython  = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$IconPath    = Join-Path $ProjectDir "assets\orezone_qhse.ico"
$DistDir     = Join-Path $ProjectDir "dist"
$AppDistDir  = Join-Path $DistDir "OREZONE_QHSE_Mobile"
$ExePath     = Join-Path $AppDistDir "OREZONE_QHSE_Mobile.exe"
$ReleaseZip  = Join-Path $DistDir "OREZONE_QHSE_Mobile_PC_INSTALLABLE.zip"

Write-Host "Generation de l'executable OREZONE QHSE Mobile (PC)" -ForegroundColor Blue
Write-Host "Dossier projet: $ProjectDir"

if (-not (Test-Path $VenvPython)) {
    throw "Environnement .venv introuvable. Lance d'abord install_orezone_qhse.bat."
}

# ── 1. Dependances build ─────────────────────────────────────────────────────
Write-Step "Verification des dependances build"
foreach ($pkg in @(@{mod="flet";req="flet==0.84.0"}, @{mod="reportlab";req="reportlab==4.4.9"}, @{mod="PyInstaller";req="pyinstaller"})) {
    if (-not (Test-PythonImport $pkg.mod)) {
        & $VenvPython -m pip install $pkg.req --quiet
        if ($LASTEXITCODE -ne 0) { throw "Installation $($pkg.req) impossible." }
    }
    Write-Ok "$($pkg.mod) disponible"
}

# ── 2. Cache binaire Flet ────────────────────────────────────────────────────
Write-Step "Verification du binaire Flet desktop"
$FletCacheRoot = Join-Path $env:USERPROFILE ".flet\client"
$FletExeSearch = Get-ChildItem $FletCacheRoot -Recurse -Filter "flet.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $FletExeSearch) {
    throw "Binaire Flet introuvable dans $FletCacheRoot. Lance l'application une fois pour le telecharger (~95 Mo)."
}
Write-Ok "Cache Flet pret: $($FletExeSearch.DirectoryName)"

# ── 3. Nettoyage ─────────────────────────────────────────────────────────────
Write-Step "Nettoyage des anciens fichiers de build"
$ProjectRoot = (Resolve-Path $ProjectDir).Path
foreach ($PathToClean in @((Join-Path $ProjectDir "build_mobile_exe"), $AppDistDir)) {
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

# ── 4. Compilation PyInstaller ───────────────────────────────────────────────
Write-Step "Compilation de l'application mobile (PyInstaller)"

$addDataAssets = "$(Join-Path $ProjectDir 'assets');assets"
$FletMaterialDir = Join-Path $ProjectDir ".venv\Lib\site-packages\flet\controls\material"
if (-not (Test-Path $FletMaterialDir)) {
    throw "Ressources Flet introuvables: $FletMaterialDir"
}
$addDataFletMaterial = "$FletMaterialDir;flet\controls\material"

$iconArg = @()
if (Test-Path $IconPath) { $iconArg = @("--icon", $IconPath) }

$ErrorActionPreference = "Continue"
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "OREZONE_QHSE_Mobile" `
    --distpath "$DistDir" `
    --workpath "$ProjectDir\build_mobile_exe" `
    --specpath "$ProjectDir\build_mobile_exe" `
    --add-data "$addDataAssets" `
    --add-data "$addDataFletMaterial" `
    @iconArg `
    "mobile_app.py"
$ErrorActionPreference = "Stop"

if ($LASTEXITCODE -ne 0) { throw "Compilation PyInstaller echouee." }
if (-not (Test-Path $ExePath))  { throw "Executable non trouve apres compilation: $ExePath" }
Write-Ok "Executable cree: $ExePath"

# ── 5. Verification bundle Flet ──────────────────────────────────────────────
Write-Step "Verification du bundle Flet offline"
$FletExeInBundle = Join-Path $AppDistDir "_internal\flet_desktop\app\flet\flet.exe"
if (-not (Test-Path $FletExeInBundle)) {
    throw "flet.exe absent du bundle. Le hook Flet n'a pas fonctionne."
}
Write-Ok "Binaire Flet confirme dans le bundle"

# ── 6. Dossiers runtime ──────────────────────────────────────────────────────
Write-Step "Preparation des dossiers runtime"
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "data")    | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "exports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $AppDistDir "timesheets") | Out-Null
Write-Ok "Dossiers runtime crees"

# ── 7. Notice d'installation ─────────────────────────────────────────────────
Write-Step "Creation de la notice d'installation"
@"
OREZONE QHSE Mobile (PC) - Notice d'installation
==================================================

PRE-REQUIS
----------
- Windows 10 ou 11 (64 bits)
- Aucune installation de Python ou logiciel requis
- Connexion reseau local avec l'app principale OREZONE QHSE

INSTALLATION SUR UN AUTRE ORDINATEUR
--------------------------------------
1. Copier le dossier OREZONE_QHSE_Mobile sur le PC cible
   (ou decompresser OREZONE_QHSE_Mobile_PC_INSTALLABLE.zip)
2. Double-cliquer sur OREZONE_QHSE_Mobile.exe
3. Si Windows Defender bloque : "Informations complementaires" > "Executer quand meme"

CONFIGURATION REQUISE
---------------------
Au premier lancement, aller dans Parametres et configurer :
  - URL du serveur : ex. http://192.168.1.10:5000
  - Token d'acces (fourni par l'administrateur QHSE)

L'application principale OREZONE QHSE doit etre active
et le serveur de synchronisation mobile doit etre demarre
sur le meme reseau local.

DONNEES
-------
- Base de donnees locale : %APPDATA%\OREZONE_QHSE_Mobile\data\
- Timesheets telecharges : %APPDATA%\OREZONE_QHSE_Mobile\timesheets\
- Exports PDF           : %APPDATA%\OREZONE_QHSE_Mobile\exports\

PROBLEMES COURANTS
------------------
- Erreur 10060 (timeout) : l'app principale n'est pas demarree
  ou le serveur sync n'est pas actif
- Erreur 10061 (connexion refusee) : serveur sync non demarre
- Adresse introuvable : verifier l'URL dans Parametres

VERSION
-------
Version build : $(Get-Date -Format 'yyyy-MM-dd')
Flet          : 0.84.0
"@ | Set-Content -Path (Join-Path $AppDistDir "LIRE_AVANT_INSTALLATION.txt") -Encoding UTF8
Write-Ok "Notice creee"

# ── 8. Archive ZIP ───────────────────────────────────────────────────────────
Write-Step "Creation de l'archive installable"
for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
    try {
        Start-Sleep -Seconds 2
        Compress-Archive -Path $AppDistDir -DestinationPath $ReleaseZip -Force
        break
    } catch {
        if ($Attempt -eq 5) { throw }
        Write-Host "Archive occupee, nouvelle tentative $($Attempt+1)/5..." -ForegroundColor Yellow
    }
}
$ZipSizeMb = [math]::Round((Get-Item $ReleaseZip).Length / 1MB, 1)
Write-Ok "Archive creee ($($ZipSizeMb) Mo): $ReleaseZip"

# ── Recapitulatif ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Generation terminee avec succes." -ForegroundColor Green
Write-Host ""
Write-Host "Pour distribuer sur un autre PC :" -ForegroundColor Yellow
Write-Host "  -> Envoyer : $ReleaseZip" -ForegroundColor White
Write-Host "  -> Sur le PC cible : decompresser, puis lancer OREZONE_QHSE_Mobile.exe" -ForegroundColor White
