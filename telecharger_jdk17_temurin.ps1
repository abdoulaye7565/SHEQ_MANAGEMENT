$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$DownloadDir = Join-Path $Root "downloads"
$ToolsDir = Join-Path $Root "tools"
$Archive = Join-Path $DownloadDir "temurin-jdk-17-windows-x64.zip"
$Url = "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"

New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null

Write-Host "Telechargement JDK 17 Temurin officiel..." -ForegroundColor Cyan
Write-Host $Url -ForegroundColor DarkGray

Invoke-WebRequest -Uri $Url -OutFile $Archive

Write-Host "Archive JDK telechargee:" -ForegroundColor Green
Write-Host $Archive -ForegroundColor White

Write-Host "Extraction du JDK portable..." -ForegroundColor Cyan
tar -xf $Archive -C $ToolsDir

$java = Get-ChildItem -Path $ToolsDir -Filter java.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like "*\bin\java.exe" } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $java) {
    throw "Extraction terminee, mais java.exe est introuvable dans tools."
}

$javaHome = Split-Path -Parent (Split-Path -Parent $java.FullName)
Write-Host "JDK portable pret:" -ForegroundColor Green
Write-Host $javaHome -ForegroundColor White
Write-Host "Relance maintenant preparer_android_orezone_qhse_mobile.bat" -ForegroundColor Cyan
