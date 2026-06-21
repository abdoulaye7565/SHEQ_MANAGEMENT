param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Find-JavaHome {
    $javaCommand = Get-Command java -ErrorAction SilentlyContinue
    if ($javaCommand) {
        $javaPath = $javaCommand.Source
        $candidate = Split-Path -Parent (Split-Path -Parent $javaPath)
        if (Test-Path (Join-Path $candidate "bin\java.exe")) {
            return $candidate
        }
    }

    $roots = @(
        "$Root\tools",
        "$env:ProgramFiles\Eclipse Adoptium",
        "$env:ProgramFiles\Java",
        "$env:ProgramFiles\Microsoft",
        "${env:ProgramFiles(x86)}\Java"
    )

    foreach ($folder in $roots) {
        if (-not (Test-Path $folder)) {
            continue
        }
        $jdk = Get-ChildItem -Path $folder -Directory -Recurse -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName "bin\java.exe") } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($jdk) {
            return $jdk.FullName
        }
    }

    return $null
}

Write-Host "Preparation Android OREZONE QHSE Mobile" -ForegroundColor Cyan

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Environnement virtuel introuvable: .venv\Scripts\python.exe"
}

Write-Host "Verification Flet..." -ForegroundColor Cyan
if (-not (Test-Path ".\.venv\Scripts\flet.exe")) {
    throw "Flet introuvable: .venv\Scripts\flet.exe"
}
Write-Host "Flet OK" -ForegroundColor Green

$javaHome = Find-JavaHome
if (-not $javaHome) {
    Write-Host ""
    Write-Host "Java JDK est manquant sur ce PC." -ForegroundColor Red
    Write-Host "Installe JDK 17 Windows x64 MSI, puis relance ce fichier." -ForegroundColor Yellow
    Write-Host "Lien conseille: https://adoptium.net/temurin/releases/?version=17" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Apres installation, ferme et rouvre PowerShell, puis relance:" -ForegroundColor Yellow
    Write-Host ".\preparer_android_orezone_qhse_mobile.bat" -ForegroundColor White
    exit 1
}

$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;$env:Path"

Write-Host "Java detecte: $javaHome" -ForegroundColor Green
& "$javaHome\bin\java.exe" -version

Write-Host ""
Write-Host "Environnement Android pret cote projet." -ForegroundColor Green

if ($Build) {
    Write-Host "Lancement du build APK..." -ForegroundColor Cyan
    & ".\build_android_orezone_qhse_mobile.ps1"
} else {
    Write-Host "Pour creer l'APK maintenant, lance:" -ForegroundColor Cyan
    Write-Host ".\build_android_orezone_qhse_mobile.bat" -ForegroundColor White
}
