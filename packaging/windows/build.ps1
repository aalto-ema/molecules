# Run on Windows x64 with Python, the project, PyInstaller, and Inno Setup installed.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
Push-Location (Join-Path $PSScriptRoot '..\..')
try {
    $version = python -c "from importlib.metadata import version; print(version('molecules-editor'))"
    if ($version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+[a-zA-Z0-9.+-]*$') {
        throw "Unexpected app version: $version"
    }
    $revision = git rev-parse HEAD
    python -m PyInstaller --noconfirm --clean --windowed --onedir --noupx --name Molecules `
        --specpath build\windows --workpath build\windows\work --distpath dist `
        --collect-data molecules --additional-hooks-dir packaging\windows\hooks `
        packaging\windows\launcher.py
    python packaging\windows\collect_licenses.py dist\Molecules\Licenses $revision

    $compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
    if (-not (Test-Path $compiler)) {
        $compiler = (Get-Command ISCC.exe).Source
    }
    & $compiler "/DAppVersion=$version" 'packaging\windows\molecules.iss'
    $installer = "Molecules-$version-windows-x64-setup.exe"
    $path = Join-Path 'dist\installer' $installer
    $sha256 = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    "$sha256  $installer" | Set-Content -Path "$path.sha256" -Encoding ascii
    if ($env:GITHUB_OUTPUT) {
        "installer=dist/installer/$installer" >> $env:GITHUB_OUTPUT
    }
}
finally {
    Pop-Location
}
