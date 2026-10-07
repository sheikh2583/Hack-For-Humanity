<#
Create a current, self-contained review ZIP at the project root. It includes
source, config, notebooks, the active training requirements, runbook, legal
evidence register, and review prompt. It excludes datasets, model weights,
training outputs, environments, caches, and credentials. Run from any directory:
  .\scripts\make_review_zip.ps1
#>
[CmdletBinding()]
param(
    [string]$OutputPath = ""
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $projectRoot "kilnwatch_bd_share.zip"
} elseif (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath = Join-Path (Get-Location).Path $OutputPath
}

$include = @(
    "app", "config", "docs", "notebooks", "src", "tests", "tools",
    "scripts", "results", "AGENTS.md", "README.md", "pyproject.toml",
    ".gitignore", ".gitattributes", "requirements-gpu-cu130.txt",
    "requirements-gpu-windows-py312.txt",
    "explore_labels.py", "explore_parquet.py", "kilnwatch_scaffold.md"
)
$excludePattern = '(^|[/\\])(__pycache__|\.pytest_cache|\.ruff_cache|\.mypy_cache|\.ipynb_checkpoints|\.venv|venv|runs|wandb|\.git|\.kilo|results[/\\]run_[0-9]{4,})([/\\]|$)'
$excludeExtensions = @(".pyc", ".pt", ".pth", ".onnx", ".engine", ".parquet", ".tif", ".tiff", ".key", ".pem", ".log")
$excludeNames = @("credentials.json", "service-account.json", "training_results.json")

Push-Location $projectRoot
try {
    foreach ($path in $include) {
        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $path))) {
            throw "Review ZIP input is missing: $path"
        }
    }
    Compress-Archive -Path $include -DestinationPath $OutputPath -Force
    Add-Type -AssemblyName System.IO.Compression
    $archive = [System.IO.Compression.ZipFile]::Open(
        (Resolve-Path -LiteralPath $OutputPath),
        [System.IO.Compression.ZipArchiveMode]::Update
    )
    try {
        foreach ($entry in @($archive.Entries)) {
            $name = [System.IO.Path]::GetFileName($entry.FullName)
            $extension = [System.IO.Path]::GetExtension($name).ToLowerInvariant()
            if ($entry.FullName -match $excludePattern -or
                $extension -in $excludeExtensions -or
                $name -like ".env*" -or
                $name -in $excludeNames) {
                $entry.Delete()
            }
        }
    } finally {
        $archive.Dispose()
    }

    $check = [System.IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $OutputPath))
    try {
        $names = @($check.Entries | ForEach-Object { $_.FullName -replace '\\', '/' })
        foreach ($requiredEntry in @(
            "AGENTS.md",
            "requirements-gpu-cu130.txt",
            "requirements-gpu-windows-py312.txt",
            "docs/PROGRESS.md",
            "docs/TRAINING_READINESS.md",
            "docs/TRAINING_RUN_HISTORY.md",
            "docs/RUNBOOK.md",
            "docs/screening_provenance.md",
            "results/README.md",
            "docs/legal_basis.md",
            "docs/CLAUDE_WEB_PROMPT.md",
            "notebooks/train.ipynb"
        )) {
            if ($requiredEntry -notin $names) {
                throw "Review ZIP is missing required entry: $requiredEntry"
            }
        }
        $forbidden = @($names | Where-Object {
            $_ -match $excludePattern -or
            [System.IO.Path]::GetExtension($_).ToLowerInvariant() -in $excludeExtensions -or
            [System.IO.Path]::GetFileName($_) -in $excludeNames
        })
        if ($forbidden.Count -gt 0) {
            throw "Review ZIP contains excluded entries: $($forbidden -join ', ')"
        }
    } finally {
        $check.Dispose()
    }

    $item = Get-Item -LiteralPath $OutputPath
    Write-Output "Created and verified $($item.FullName) ($('{0:N1}' -f ($item.Length / 1MB)) MB)"
} finally {
    Pop-Location
}
