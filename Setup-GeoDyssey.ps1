param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Check-Step([string]$Step) { if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE" } }
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    Check-Step 'Python environment creation'
}
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Check-Step 'Python dependency installation'
Push-Location -LiteralPath frontend
try {
    & npm.cmd ci
    Check-Step 'React dependency installation'
    & npm.cmd run build
    Check-Step 'React build'
} finally { Pop-Location }
if (-not (Test-Path -LiteralPath 'Data\derived\manifest.json')) {
    & .\.venv\Scripts\python.exe -m scripts.extract_osm
    Check-Step 'OSM extraction'
}
Write-Host 'Setup complete. Run Start-GeoDyssey.cmd, then create an analysis in the browser.'
