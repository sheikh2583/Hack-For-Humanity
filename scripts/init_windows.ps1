[CmdletBinding()]
param(
    [string]$DatasetArchive = "",
    [switch]$SkipAssetSetup
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Assert-NativeSuccess([string]$TaskName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$TaskName failed with exit code $LASTEXITCODE"
    }
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            throw "Install Python 3.11 or 3.12, then rerun this script."
        }
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        Assert-NativeSuccess "Python version check"
        if ($version -notin @("3.11", "3.12")) {
            throw "Python 3.11 or 3.12 is required; found Python $version."
        }
        & python -m venv .venv
        Assert-NativeSuccess "Virtual environment creation"
    }

    & $venvPython -c "import sys; assert sys.version_info[:2] in {(3, 11), (3, 12)}, f'Unsupported Python: {sys.version}'"
    Assert-NativeSuccess "Virtual environment Python check"
    & $venvPython -m pip install --upgrade pip
    Assert-NativeSuccess "pip upgrade"
    & $venvPython -m pip install -e ".[dev,detect,training]" -r requirements-gpu-cu130.txt
    Assert-NativeSuccess "Project and GPU dependency installation"

    if (-not $SkipAssetSetup) {
        $assetArgs = @()
        if ($DatasetArchive) { $assetArgs += @("--dataset-archive", $DatasetArchive) }
        & $venvPython scripts/prepare_training_assets.py @assetArgs
        Assert-NativeSuccess "Training asset preparation"
    }

    Write-Output "Environment setup is complete. No GPU training or smoke test was started."
    Write-Output "From the project root, run: .\scripts\train_windows.ps1 smoke"
    Write-Output "After it passes, start or resume configured stages: .\scripts\train_windows.ps1 full"
    Write-Output "Runner options: .\.venv\Scripts\python.exe scripts\train.py --help"
} finally {
    Pop-Location
}
