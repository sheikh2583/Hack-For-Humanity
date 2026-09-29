[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "continue", "smoke", "full")]
    [string]$Command = "start",
    [string]$RunId = "",
    [string]$Dataset = "",
    [string]$Device = "0",
    [string]$Config = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Run: powershell -ExecutionPolicy Bypass -File .\scripts\init_windows.ps1"
}
Push-Location $projectRoot
try {
    $runnerArgs = @("scripts/train.py", $Command, "--device", $Device)
    if ($RunId) { $runnerArgs += @("--run-id", $RunId) }
    if ($Dataset) { $runnerArgs += @("--dataset", $Dataset) }
    if ($Config) { $runnerArgs += @("--config", $Config) }
    & $python @runnerArgs
    if ($LASTEXITCODE -ne 0) { throw "Training runner exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
