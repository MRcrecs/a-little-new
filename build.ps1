$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "url-auto-opener" `
    main.py
