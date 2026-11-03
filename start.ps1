$ErrorActionPreference = 'Stop'
$pythonExecutable = $null
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
if (Test-Path -LiteralPath $installRoot) {
    $candidate = Get-ChildItem -LiteralPath $installRoot -Directory | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'python.exe' } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($candidate) { $pythonExecutable = $candidate }
}
if (-not $pythonExecutable) {
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) { $pythonExecutable = $candidate.Source }
}
if ($pythonExecutable) {
    & $pythonExecutable (Join-Path $PSScriptRoot 'server.py')
} else {
    & py -3 (Join-Path $PSScriptRoot 'server.py')
}
