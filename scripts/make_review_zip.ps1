<#
Create a small review ZIP at the project root, excluding datasets, environments,
caches, credentials, and model weights. Run from any directory:
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
    "scripts", "AGENTS.md", "README.md", "pyproject.toml",
    "explore_labels.py", "explore_parquet.py", "kilnwatch_scaffold.md"
)
$excludePattern = '(^|[/\\])(__pycache__|\.pytest_cache|\.ruff_cache|\.ipynb_checkpoints|\.venv|venv)([/\\]|$)'
$excludeExtensions = @(".pyc", ".pt", ".pth", ".onnx", ".key", ".pem")
$excludeNames = @("credentials.json", "service-account.json")

Push-Location $projectRoot
try {
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
    $item = Get-Item -LiteralPath $OutputPath
    Write-Output "Created $($item.FullName) ($('{0:N1}' -f ($item.Length / 1MB)) MB)"
} finally {
    Pop-Location
}
