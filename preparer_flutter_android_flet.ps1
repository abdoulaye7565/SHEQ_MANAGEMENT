param(
    [string]$FlutterVersion = "3.41.4",
    [ValidateSet("auto", "bits", "curl")]
    [string]$Method = "auto"
)

$ErrorActionPreference = "Stop"
$HomeDir = [Environment]::GetFolderPath("UserProfile")
$FlutterRoot = Join-Path $HomeDir "flutter"
$InstallDir = Join-Path $FlutterRoot $FlutterVersion
$TempDir = Join-Path $FlutterRoot "${FlutterVersion}_temp"
$Archive = Join-Path $HomeDir "flutter_windows_$FlutterVersion-stable.zip"
$Url = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_$FlutterVersion-stable.zip"
$LockPath = Join-Path $HomeDir "flutter_windows_$FlutterVersion-stable.lock"

if (Test-Path (Join-Path $InstallDir "bin\flutter.bat")) {
    Write-Host "Flutter deja pret: $InstallDir" -ForegroundColor Green
    exit 0
}

if (Test-Path $LockPath) {
    $lockAge = (Get-Date) - (Get-Item $LockPath).LastWriteTime
    if ($lockAge.TotalMinutes -lt 30) {
        throw "Un telechargement Flutter semble deja en cours. Attends ou supprime le fichier lock: $LockPath"
    }
    Remove-Item -LiteralPath $LockPath -Force
}
New-Item -ItemType File -Path $LockPath -Force | Out-Null

try {

New-Item -ItemType Directory -Path $FlutterRoot -Force | Out-Null

Write-Host "Preparation Flutter SDK $FlutterVersion pour Flet Android" -ForegroundColor Cyan
Write-Host "URL: $Url" -ForegroundColor DarkGray
Write-Host "Archive: $Archive" -ForegroundColor DarkGray

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue

function Test-Archive {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $false
    }
    $python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
    if (Test-Path $python) {
        & $python -c "import sys, zipfile; z=zipfile.ZipFile(sys.argv[1]); sys.exit(0 if z.testzip() is None else 1)" $Path
        return $LASTEXITCODE -eq 0
    }
    cmd.exe /c "tar -tf `"$Path`" >nul 2>nul"
    return $LASTEXITCODE -eq 0
}

function Download-WithCurl {
    if (-not $curl) {
        throw "curl.exe introuvable."
    }
    for ($attempt = 1; $attempt -le 8; $attempt++) {
        Write-Host "Telechargement Flutter via curl tentative $attempt/8..." -ForegroundColor Cyan
        & curl.exe --ipv4 -L --retry 15 --retry-all-errors --retry-delay 5 --connect-timeout 60 --speed-limit 1024 --speed-time 90 -C - -o $Archive $Url
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        Write-Host "curl interrompu. Reprise dans 10 secondes..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
    return $false
}

function Download-WithBits {
    Write-Host "Telechargement Flutter via BITS Windows..." -ForegroundColor Cyan
    Import-Module BitsTransfer -ErrorAction Stop
    $job = Start-BitsTransfer -Source $Url -Destination $Archive -DisplayName "OREZONE Flutter SDK $FlutterVersion" -Asynchronous -ErrorAction Stop
    try {
        while ($job.JobState -in @("Connecting", "Transferring", "Queued")) {
            $job = Get-BitsTransfer -Id $job.Id
            $bytesTotal = [double]$job.BytesTotal
            $percent = 0
            if ($bytesTotal -gt 0) {
                $percent = [math]::Round(($job.BytesTransferred / $bytesTotal) * 100, 1)
            }
            Write-Host ("BITS: {0}% ({1:N0}/{2:N0} octets)" -f $percent, $job.BytesTransferred, $job.BytesTotal) -ForegroundColor DarkCyan
            Start-Sleep -Seconds 20
        }
        $job = Get-BitsTransfer -Id $job.Id
        if ($job.JobState -eq "Transferred") {
            Complete-BitsTransfer -BitsJob $job
            return $true
        }
        Write-Host "BITS termine avec l'etat: $($job.JobState)" -ForegroundColor Yellow
        Remove-BitsTransfer -BitsJob $job -ErrorAction SilentlyContinue
        return $false
    } catch {
        Remove-BitsTransfer -BitsJob $job -ErrorAction SilentlyContinue
        throw
    }
}

if (-not (Test-Archive $Archive)) {
    $downloaded = $false
    if ($Method -in @("auto", "bits")) {
        try {
            $downloaded = Download-WithBits
        } catch {
            Write-Host "BITS indisponible ou interrompu: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    if (-not $downloaded -and $Method -in @("auto", "curl")) {
        $downloaded = Download-WithCurl
    }
    if (-not $downloaded) {
        throw "Telechargement Flutter echoue. Relance ce script quand Internet est stable; il reprendra le fichier partiel."
    }
}

Write-Host "Verification archive Flutter..." -ForegroundColor Cyan
if (-not (Test-Archive $Archive)) {
    throw "Archive Flutter incomplete. Relance le script pour reprendre le telechargement."
}

if (Test-Path $TempDir) {
    Remove-Item -LiteralPath $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host "Extraction Flutter..." -ForegroundColor Cyan
tar -xf $Archive -C $TempDir

$ExtractedFlutter = Join-Path $TempDir "flutter"
if (-not (Test-Path (Join-Path $ExtractedFlutter "bin\flutter.bat"))) {
    throw "Extraction Flutter invalide: flutter.bat introuvable."
}

if (Test-Path $InstallDir) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}
Move-Item -LiteralPath $ExtractedFlutter -Destination $InstallDir
Remove-Item -LiteralPath $TempDir -Recurse -Force

Write-Host "Flutter installe pour Flet:" -ForegroundColor Green
Write-Host $InstallDir -ForegroundColor White
} finally {
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}
