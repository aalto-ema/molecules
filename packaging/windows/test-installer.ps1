$ErrorActionPreference = 'Stop'

function Invoke-CheckedProcess($Path, $Arguments) {
    $process = Start-Process -FilePath $Path -ArgumentList $Arguments -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        throw "$Path exited with code $($process.ExitCode)"
    }
}

$smokeOutput = Join-Path $env:RUNNER_TEMP 'Molecules installer smoke test'
$installLog = Join-Path $env:RUNNER_TEMP 'molecules-install.log'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\Molecules'
$app = Join-Path $installDir 'Molecules.exe'
$uninstaller = Join-Path $installDir 'unins000.exe'
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Molecules.lnk'
try {
    Invoke-CheckedProcess (Resolve-Path $env:INSTALLER_PATH).Path @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$installLog`""
    )
    if (-not (Test-Path $shortcut)) {
        throw 'Start menu shortcut is missing.'
    }
    Invoke-CheckedProcess $app @('--smoke-test', "`"$smokeOutput`"")
    if (-not (Test-Path (Join-Path $smokeOutput 'smoke-test.txt'))) {
        throw 'Installed app did not write a smoke test report.'
    }
    Invoke-CheckedProcess $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    if ((Test-Path $app) -or (Test-Path $shortcut)) {
        throw 'Uninstall left the app executable or its Start menu shortcut behind.'
    }
    if (-not (Test-Path (Join-Path $smokeOutput 'ethanol.molecules.json'))) {
        throw 'Uninstall removed a saved drawing.'
    }
}
catch {
    if (Test-Path $installLog) { Get-Content $installLog -Tail 70 }
    throw
}
finally {
    $report = Join-Path $smokeOutput 'smoke-test.txt'
    if (Test-Path $report) { Get-Content $report }
}
