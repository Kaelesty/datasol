Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$srcPath = Join-Path $projectRoot "src"

$env:PYTHONPATH = $srcPath

Write-Host "Starting Datssol web UI backend with auto-reload..." -ForegroundColor Cyan
Write-Host "Project root: $projectRoot" -ForegroundColor DarkGray
Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor DarkGray

python -m flask --app datssol.ui.web_app:create_app run --debug --host 127.0.0.1 --port 8765
