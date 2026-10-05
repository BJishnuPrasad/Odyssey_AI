$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$atlasPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $atlasPython)) { throw 'Run Setup-GeoDyssey.ps1 first to install the project environment.' }
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Build the frontend first: cd frontend; npm.cmd run build' }
Write-Host 'GeoDyssey: http://127.0.0.1:8000  |  API docs: http://127.0.0.1:8000/docs'
Write-Host 'Keep this terminal open. Press Ctrl+C to stop. Run only one server instance.'
& $atlasPython -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
