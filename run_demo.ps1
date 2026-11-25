$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python environment missing. Run uv sync --locked first.'
}

function Resolve-AntigravityExecutable {
    $configured = if ($env:ANTIGRAVITY_EXECUTABLE) { $env:ANTIGRAVITY_EXECUTABLE.Trim() } else { '' }
    if ($configured) {
        if (Test-Path -LiteralPath $configured -PathType Leaf) {
            if ($configured -notmatch '\.exe$') {
                throw "ANTIGRAVITY_EXECUTABLE must point to a native .exe on Windows (got '$configured')."
            }
            return (Resolve-Path -LiteralPath $configured).Path
        }
        $cmd = Get-Command $configured -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -match '\.exe$') {
            return $cmd.Source
        }
        throw "Configured ANTIGRAVITY_EXECUTABLE '$configured' was not found or is not a native .exe."
    }

    $fromPath = Get-Command agy -ErrorAction SilentlyContinue
    if ($fromPath -and $fromPath.Source -match '\.exe$') {
        return $fromPath.Source
    }

    if ($env:LOCALAPPDATA) {
        $defaultLocal = Join-Path $env:LOCALAPPDATA 'agy\bin\agy.exe'
        if (Test-Path -LiteralPath $defaultLocal -PathType Leaf) {
            $env:ANTIGRAVITY_EXECUTABLE = $defaultLocal
            return $defaultLocal
        }
    }

    throw 'Antigravity CLI (agy) is missing. Install it, sign in, or set $env:ANTIGRAVITY_EXECUTABLE to agy.exe before starting Demo.'
}

$agyExe = Resolve-AntigravityExecutable

$selectedModel = if ($env:ANTIGRAVITY_MODEL) { $env:ANTIGRAVITY_MODEL } else { 'gemini-3.8-flash-medium' }
$ErrorActionPreference = 'Continue'
$modelList = & $agyExe models 2>&1
$modelCheckExitCode = $LASTEXITCODE
$ErrorActionPreference = 'Stop'
if ($modelCheckExitCode -ne 0 -or -not ($modelList | Select-String -SimpleMatch $selectedModel -Quiet)) {
    throw "Antigravity model '$selectedModel' is unavailable. Run 'agy' to sign in, then 'agy models'."
}

$env:EVALUATION_PROVIDER = 'antigravity'
if (-not $env:GEMINI_MAX_RETRIES) { $env:GEMINI_MAX_RETRIES = '0' }
$selectedTimeout = if ($env:ANTIGRAVITY_TIMEOUT_SECONDS) { $env:ANTIGRAVITY_TIMEOUT_SECONDS } else { '120' }
Write-Host "Starting Demo with live Antigravity model $selectedModel (timeout ${selectedTimeout}s per attempt, automatic retries $env:GEMINI_MAX_RETRIES)"
& $python -m uvicorn source.main:create_app --factory --host 127.0.0.1 --port 8000
