param(
    [ValidateSet("start", "status", "stop", "restart")]
    [string]$Action = "start",
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$repo = $PSScriptRoot
Set-Location -LiteralPath $repo
$Host.UI.RawUI.WindowTitle = "GenBox Lab - DO NOT CLOSE"

$arguments = @("scripts/genbox_lab.py", $Action)
if ($Background) { $arguments += "--background" }

python @arguments
exit $LASTEXITCODE
