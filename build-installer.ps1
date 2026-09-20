param(
    [string]$Python = '',
    [string]$Iscc = '',
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$taskProject = $PSScriptRoot
if (-not $Python) {
    $taskVenv = Join-Path $taskProject 'backend\.venv\Scripts\python.exe'
    $Python = if (Test-Path -LiteralPath $taskVenv) { $taskVenv } else { 'python' }
}
$taskOldPythonPath = $env:PYTHONPATH
Push-Location -LiteralPath $taskProject
try {
    $env:PYTHONPATH = Join-Path $taskProject 'backend'
    $taskIdentityJson = & $Python -c 'import json; from liquidacao_custom.metadata import APP_VERSION,APP_DISPLAY_VERSION,APP_ID,EXECUTABLE_NAME; print(json.dumps(dict(version=APP_VERSION,display_version=APP_DISPLAY_VERSION,app_id=APP_ID,executable=EXECUTABLE_NAME)))'
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível ler a identificação do aplicativo.' }
    $taskIdentity = $taskIdentityJson | ConvertFrom-Json

    if (-not $Iscc) {
        $taskCandidates = @(
            (Join-Path $taskProject '.tools\InnoSetup7\ISCC.exe'),
            (Join-Path ${env:ProgramFiles} 'Inno Setup 7\ISCC.exe'),
            (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe')
        )
        $taskDetected = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($taskDetected) { $taskCandidates += $taskDetected.Source }
        $Iscc = $taskCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if (-not $Iscc) { throw 'Inno Setup não foi encontrado.' }

    if (-not $SkipBuild) {
        & (Join-Path $taskProject 'build.ps1') -Python $Python
    }
    $taskPayload = Join-Path $taskProject 'dist-installed\CalculosJuridicos'
    $taskExecutable = Join-Path $taskPayload $taskIdentity.executable
    if (-not (Test-Path -LiteralPath $taskExecutable)) { throw 'Executável ausente.' }
    if ((Get-Item -LiteralPath $taskExecutable).VersionInfo.FileVersion -ne $taskIdentity.version) {
        throw 'A versão do executável difere do código.'
    }

    $taskOutput = Join-Path $taskProject ('instaladores\' + $taskIdentity.version)
    New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
    $taskArguments = @(
        ('/DAppVersion=' + $taskIdentity.version),
        ('/DAppDisplayVersion=' + $taskIdentity.display_version),
        ('/DAppIdValue=' + $taskIdentity.app_id),
        ('/DPayloadDir=' + $taskPayload),
        ('/DInstallerOutput=' + $taskOutput),
        (Join-Path $taskProject 'installer\CalculosJuridicos.iss')
    )
    $taskLog = Join-Path $taskOutput 'compilacao-inno.log'
    & $Iscc @taskArguments *> $taskLog
    if ($LASTEXITCODE -ne 0) {
        Get-Content -LiteralPath $taskLog -Tail 30
        throw 'O instalador não pôde ser compilado.'
    }
    $taskInstaller = Join-Path $taskOutput ('CalculosJuridicos-Setup-' + $taskIdentity.version + '-x64.exe')
    $taskHash = (Get-FileHash -LiteralPath $taskInstaller -Algorithm SHA256).Hash.ToLowerInvariant()
    ($taskHash + '  ' + (Split-Path -Leaf $taskInstaller)) | Set-Content -LiteralPath ($taskInstaller + '.sha256') -Encoding ASCII

    $taskFriendlyOutput = Join-Path $taskProject ('instaladores\' + $taskIdentity.display_version)
    New-Item -ItemType Directory -Path $taskFriendlyOutput -Force | Out-Null
    $taskFriendly = Join-Path $taskFriendlyOutput ('CalculosJuridicos-Setup-' + $taskIdentity.display_version + '-x64.exe')
    Copy-Item -LiteralPath $taskInstaller -Destination $taskFriendly -Force
    ($taskHash + '  ' + (Split-Path -Leaf $taskFriendly)) | Set-Content -LiteralPath ($taskFriendly + '.sha256') -Encoding ASCII
    Write-Host ('Instalador criado: ' + $taskFriendly)
}
finally {
    $env:PYTHONPATH = $taskOldPythonPath
    Pop-Location
}
