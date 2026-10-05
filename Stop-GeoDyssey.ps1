$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'runtime\server.pid')) {
    Write-Host 'No background server PID recorded. Use Ctrl+C in the launcher terminal.'
    exit 0
}
$atlasPid = [int](Get-Content -LiteralPath 'runtime\server.pid')
$atlasProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $atlasPid"
$atlasExpected = (Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path
if (-not $atlasProcess) { Write-Host 'The recorded background server has stopped.'; exit 0 }
if ($atlasProcess.ExecutablePath -ne $atlasExpected -or $atlasProcess.CommandLine -notmatch 'uvicorn backend.api:app') {
    throw 'The recorded process does not match this project. No process was stopped.'
}
# The venv launcher may own a child Python process; stop only this verified tree.
& taskkill.exe /PID $atlasPid /T /F
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the background server.' }
