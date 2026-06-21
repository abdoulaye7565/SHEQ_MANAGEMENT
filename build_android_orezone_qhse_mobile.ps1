param(
    [string]$AppName = "OREZONE QHSE Mobile",
    [string]$BuildVersion = "1.3.0",
    [int]$BuildNumber = 10,
    [switch]$ClearCache
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

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

function Test-WindowsDeveloperMode {
    if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
        return $true
    }

    $key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    try {
        $value = Get-ItemProperty -Path $key -Name "AllowDevelopmentWithoutDevLicense" -ErrorAction Stop
        return [int]$value.AllowDevelopmentWithoutDevLicense -eq 1
    } catch {
        return $false
    }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Environnement virtuel introuvable: .venv\Scripts\python.exe"
}

$javaHome = Find-JavaHome
if (-not $javaHome) {
    throw "Java JDK introuvable. Lance d'abord preparer_android_orezone_qhse_mobile.bat et installe JDK 17 si demande."
}
$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;$env:Path"
Write-Host "Java utilise: $javaHome" -ForegroundColor Green

$androidSdk = Join-Path $env:USERPROFILE "Android\sdk"
if (Test-Path $androidSdk) {
    $env:ANDROID_HOME = $androidSdk
    $env:ANDROID_SDK_ROOT = $androidSdk
    $platformTools = Join-Path $androidSdk "platform-tools"
    if (Test-Path $platformTools) {
        $env:Path = "$platformTools;$env:Path"
    }
}

Write-Host "Verification de Flet..." -ForegroundColor Cyan
if (-not (Test-Path ".\.venv\Scripts\flet.exe")) {
    throw "Flet introuvable: .venv\Scripts\flet.exe"
}

Write-Host "Build Android APK: $AppName" -ForegroundColor Cyan
Write-Host "Note: le premier build peut telecharger Android SDK/Gradle selon l'environnement." -ForegroundColor Yellow

if (-not (Test-WindowsDeveloperMode)) {
    throw "Mode Developpeur Windows non active. Active Parametres Windows > Confidentialite et securite > Pour les developpeurs > Mode Developpeur, ou lance activer_mode_developpeur_windows.bat, puis relance ce script."
}

if (-not (Test-Path "$env:USERPROFILE\flutter\3.41.4\bin\flutter.bat")) {
    Write-Host "Flutter SDK requis par Flet absent. Preparation Flutter..." -ForegroundColor Cyan
    & ".\preparer_flutter_android_flet.ps1" -FlutterVersion "3.41.4"
}

$mobileBuildRoot = Join-Path $Root "build_mobile_android"
$mobileAppRoot = Join-Path $mobileBuildRoot "app"
New-Item -ItemType Directory -Path $mobileAppRoot -Force | Out-Null

$itemsToCopy = @("app", "assets", "mobile_app.py", "requirements.txt")
foreach ($item in $itemsToCopy) {
    $source = Join-Path $Root $item
    $destination = Join-Path $mobileAppRoot $item
    if (Test-Path $destination) {
        Remove-Item -LiteralPath $destination -Recurse -Force
    }
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

$buildArgs = @(
    "-c", "from flet_cli.cli import main; main()",
    "build", "apk", $mobileAppRoot,
    "--module-name", "mobile_app",
    "--project", "orezone_qhse_mobile",
    "--product", $AppName,
    "--build-version", $BuildVersion,
    "--build-number", "$BuildNumber",
    "--yes",
    "--no-rich-output"
)
if ($ClearCache) {
    $buildArgs += "--clear-cache"
}

& ".\.venv\Scripts\python.exe" @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "Build Android echoue. Code sortie: $LASTEXITCODE"
}

$apk = Get-ChildItem -Path "$mobileAppRoot\build", "$Root\build", "$Root\dist" -Filter "*.apk" -Recurse -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($apk) {
    $deliveryDir = Join-Path $Root "exports"
    $deliveryApk = Join-Path $deliveryDir "OREZONE_QHSE_Mobile_Android.apk"
    New-Item -ItemType Directory -Path $deliveryDir -Force | Out-Null
    Copy-Item -LiteralPath $apk.FullName -Destination $deliveryApk -Force
    $deliveryFile = Get-Item $deliveryApk
    $deliveryHash = Get-FileHash $deliveryApk -Algorithm SHA256

    Write-Host "APK cree:" -ForegroundColor Green
    Write-Host $deliveryFile.FullName -ForegroundColor White
    Write-Host "Taille: $([math]::Round($deliveryFile.Length / 1MB, 2)) MB" -ForegroundColor White
    Write-Host "SHA256: $($deliveryHash.Hash)" -ForegroundColor DarkGray
} else {
    Write-Host "Build termine. Aucun APK trouve automatiquement; verifie le dossier build ou dist selon la sortie Flet." -ForegroundColor Yellow
}
