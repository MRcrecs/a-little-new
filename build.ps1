$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$releaseRoot = Join-Path $projectRoot "release"
$releaseDir = Join-Path $releaseRoot "url-auto-opener"

if (Test-Path $releaseDir) {
    Remove-Item $releaseDir -Recurse -Force
}

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "url-auto-opener" `
    main.py

Copy-Item ".\dist\url-auto-opener.exe" $releaseDir
Copy-Item ".\README.md" $releaseDir
