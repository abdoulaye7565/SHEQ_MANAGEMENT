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

function Write-Warn {
    param([string]$Message)
    Write-Host "!!  $Message" -ForegroundColor Yellow
}

function Get-PythonCommand {
    $candidates = @(
        @("python", "--version"),
        @("py", "-3.12", "--version"),
        @("py", "-3", "--version")
    )

    foreach ($candidate in $candidates) {
        $command = $candidate[0]
        $arguments = $candidate[1..($candidate.Length - 1)]
        try {
            $process = Start-Process -FilePath $command -ArgumentList $arguments -NoNewWindow -PassThru -Wait -RedirectStandardOutput "$env:TEMP\orezone_python_check.out" -RedirectStandardError "$env:TEMP\orezone_python_check.err"
            if ($process.ExitCode -eq 0) {
                if ($command -eq "py") {
                    if ($arguments[0] -eq "-3.12") {
                        return @{ File = "py"; Args = @("-3.12") }
                    }
                    return @{ File = "py"; Args = @("-3") }
                }
                return @{ File = "python"; Args = @() }
            }
        }
        catch {
        }
    }
    return $null
}

function Invoke-Python {
    param(
        [hashtable]$Python,
        [string[]]$Arguments
    )
    & $Python.File @($Python.Args + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "La commande Python a echoue: $($Python.File) $($Python.Args + $Arguments -join ' ')"
    }
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$SilentLauncher = Join-Path $ProjectDir "lancer_orezone_qhse_silencieux.vbs"
$IconPath = Join-Path $ProjectDir "assets\orezone_qhse.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "OREZONE QHSE.lnk"

Write-Host "Installation OREZONE QHSE" -ForegroundColor Blue
Write-Host "Dossier application: $ProjectDir"

Write-Step "Verification de Python"
$Python = Get-PythonCommand

if ($null -eq $Python) {
    Write-Warn "Python n'est pas detecte. Tentative d'installation avec winget."
    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $Winget) {
        throw "winget est introuvable. Installe Python 3.12 manuellement depuis https://www.python.org/downloads/, puis relance ce fichier."
    }

    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Installation Python via winget impossible. Installe Python 3.12 manuellement, puis relance ce fichier."
    }

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $Python = Get-PythonCommand
    if ($null -eq $Python) {
        throw "Python a ete installe mais n'est pas encore detecte. Ferme cette fenetre, ouvre une nouvelle session Windows ou PowerShell, puis relance l'installation."
    }
}

Write-Ok "Python detecte"

Write-Step "Creation de l'environnement virtuel"
if (-not (Test-Path $VenvPython)) {
    Invoke-Python $Python @("-m", "venv", ".venv")
}
Write-Ok "Environnement virtuel pret"

Write-Step "Installation des bibliotheques Python"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Mise a jour pip impossible." }

& $VenvPython -m pip install -r "requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Installation requirements.txt impossible." }

if (Test-Path (Join-Path $ProjectDir "requirements-reports.txt")) {
    & $VenvPython -m pip install -r "requirements-reports.txt"
    if ($LASTEXITCODE -ne 0) { throw "Installation requirements-reports.txt impossible." }
}
Write-Ok "Bibliotheques installees"

Write-Step "Verification des dossiers de travail"
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "data") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "exports") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "backups") | Out-Null
Write-Ok "Dossiers prets"

Write-Step "Initialisation de la base SQLite"
& $VenvPython -c "from app.db.connection import initialize_database; initialize_database(); print('Database ready')"
if ($LASTEXITCODE -ne 0) {
    throw "Initialisation de la base SQLite impossible."
}
Write-Ok "Base SQLite initialisee"

Write-Step "Creation du raccourci Bureau"
if (-not (Test-Path $SilentLauncher)) {
    throw "Lanceur silencieux introuvable: $SilentLauncher"
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
$Shortcut.Arguments = "`"$SilentLauncher`""
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Lancer OREZONE QHSE"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()
Write-Ok "Raccourci cree: $ShortcutPath"

Write-Step "Test rapide de l'application"
& $VenvPython -m compileall "app" "tests" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Verification technique impossible."
}
Write-Ok "Verification terminee"

Write-Host ""
Write-Host "Installation terminee avec succes." -ForegroundColor Green
Write-Host "Tu peux lancer OREZONE QHSE depuis le raccourci du Bureau." -ForegroundColor Green
