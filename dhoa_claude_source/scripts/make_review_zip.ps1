<#
Create the portable Claude review ZIP using the shared cross-platform Python builder.
Run from any directory with Python available on PATH:
  .\scripts\make_review_zip.ps1 [-OutputPath <path>]
#>
[CmdletBinding()]
param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$builder = Join-Path $PSScriptRoot "make_review_zip.py"
$python = Get-Command python -ErrorAction Stop

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    & $python.Source $builder
} else {
    & $python.Source $builder $OutputPath
}
exit $LASTEXITCODE
