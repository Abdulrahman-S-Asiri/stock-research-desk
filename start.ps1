$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Run setup.ps1 first.'
}
Write-Host 'Open http://127.0.0.1:8765 in your browser. Press Ctrl+C here to stop.'
& '.venv\Scripts\python.exe' app.py
