$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python environment missing. Run uv sync --locked first.'
}
if (-not (Get-Command agy -ErrorAction SilentlyContinue)) {
    throw 'Antigravity CLI (agy) is missing. Install it and sign in before starting Demo.'
}

$selectedModel = if ($env:ANTIGRAVITY_MODEL) { $env:ANTIGRAVITY_MODEL } else { 'gemini-3.8-flash-medium' }
$ErrorActionPreference = 'Continue'
$modelList = & agy models 2>&1
$modelCheckExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($modelCheckExitCode -ne 0 -or -not ($modelList | Select-String -SimpleMatch $selectedModel -Quiet)) {
    throw "Antigravity model '$selectedModel' is unavailable. Run 'agy' to sign in, then 'agy models'."
}

$env:EVALUATION_PROVIDER = 'antigravity'
Write-Host "Starting Demo with live Antigravity model $selectedModel"
& $python -m uvicorn source.main:create_app --factory --host 127.0.0.1 --port 8000
