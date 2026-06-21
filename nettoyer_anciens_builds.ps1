param(
    [switch]$Confirmer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$ProtectedNames = @("build", "build_mobile_android", "dist")
$Candidates = Get-ChildItem -LiteralPath $ProjectRoot -Directory |
    Where-Object {
        ($_.Name -like "build_*" -or $_.Name -like "dist_*") -and
        $_.Name -notin $ProtectedNames
    }

if (-not $Candidates) {
    Write-Host "Aucun ancien build a nettoyer." -ForegroundColor Green
    exit 0
}

$TotalBytes = ($Candidates | ForEach-Object {
    (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum).Sum
} | Measure-Object -Sum).Sum

Write-Host "Anciens builds detectes: $($Candidates.Count)"
Write-Host ("Espace recuperable: {0:N1} MB" -f ($TotalBytes / 1MB))
$Candidates.Name | ForEach-Object { Write-Host " - $_" }

if (-not $Confirmer) {
    Write-Host "Aucune suppression effectuee. Relancer avec -Confirmer pour nettoyer." -ForegroundColor Yellow
    exit 0
}

foreach ($Candidate in $Candidates) {
    $Resolved = (Resolve-Path -LiteralPath $Candidate.FullName).Path
    if (-not $Resolved.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Suppression refusee hors projet: $Resolved"
    }
    Remove-Item -LiteralPath $Resolved -Recurse -Force
}
Write-Host "Anciens builds nettoyes." -ForegroundColor Green
