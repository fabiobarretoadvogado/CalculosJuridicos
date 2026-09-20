param([string]$Python = '')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$taskProject = $PSScriptRoot
if (-not $Python) {
    $taskVenv = Join-Path $taskProject 'backend\.venv\Scripts\python.exe'
    $Python = if (Test-Path -LiteralPath $taskVenv) { $taskVenv } else { 'python' }
}
$taskOldPythonPath = $env:PYTHONPATH
$taskOldConsole = $env:CALCULOS_BUILD_CONSOLE
Push-Location -LiteralPath $taskProject
try {
    $env:PYTHONPATH = Join-Path $taskProject 'backend'
    Remove-Item Env:CALCULOS_BUILD_CONSOLE -ErrorAction SilentlyContinue

    Push-Location -LiteralPath (Join-Path $taskProject 'frontend')
    try {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'A interface não pôde ser compilada.' }
    }
    finally { Pop-Location }

    $taskWeb = [IO.Path]::GetFullPath((Join-Path $taskProject 'backend\liquidacao_custom\web'))
    $taskProjectPrefix = [IO.Path]::GetFullPath($taskProject).TrimEnd('\') + '\'
    if (-not ($taskWeb + '\').StartsWith($taskProjectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Pasta da interface fora do projeto.'
    }
    New-Item -ItemType Directory -Path $taskWeb -Force | Out-Null
    foreach ($taskItem in @(Get-ChildItem -LiteralPath $taskWeb -Force | Where-Object Name -ne '.gitkeep')) {
        $taskResolved = [IO.Path]::GetFullPath($taskItem.FullName)
        if (-not ($taskResolved + '\').StartsWith(($taskWeb.TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Arquivo gerado fora da pasta da interface.'
        }
        Remove-Item -LiteralPath $taskResolved -Recurse -Force
    }
    Copy-Item -Path (Join-Path $taskProject 'frontend\dist\*') -Destination $taskWeb -Recurse -Force

    & $Python (Join-Path $taskProject 'scripts\make_icon.py')
    if ($LASTEXITCODE -ne 0) { throw 'O ícone do aplicativo não pôde ser criado.' }

    $taskDist = Join-Path $taskProject 'dist-installed'
    $taskPayload = Join-Path $taskDist 'CalculosJuridicos'
    if (Test-Path -LiteralPath $taskPayload) {
        $taskArchiveRoot = Join-Path $taskProject 'build\previous-packages'
        New-Item -ItemType Directory -Path $taskArchiveRoot -Force | Out-Null
        $taskArchive = Join-Path $taskArchiveRoot ('CalculosJuridicos-' + [guid]::NewGuid().ToString('N'))
        Move-Item -LiteralPath $taskPayload -Destination $taskArchive
    }
    & $Python -m PyInstaller --noconfirm --distpath $taskDist --workpath (Join-Path $taskProject 'build\pyinstaller') (Join-Path $taskProject 'CalculosJuridicos.spec')
    if ($LASTEXITCODE -ne 0) { throw 'A geração do aplicativo falhou.' }

    & $Python (Join-Path $taskProject 'scripts\prepare_installer.py') $taskPayload
    if ($LASTEXITCODE -ne 0) { throw 'O pacote não pôde ser preparado.' }

    $taskExecutable = Join-Path $taskPayload 'CalculosJuridicos.exe'
    $taskCheck = Start-Process -FilePath $taskExecutable -ArgumentList '--self-check' -WindowStyle Hidden -PassThru -Wait
    if ($taskCheck.ExitCode -ne 0) { throw 'O aplicativo empacotado não passou na verificação interna.' }
    Write-Host 'Verificação interna do aplicativo: aprovada.'
    Write-Host ('Aplicativo criado: ' + $taskExecutable)
}
finally {
    $env:PYTHONPATH = $taskOldPythonPath
    $env:CALCULOS_BUILD_CONSOLE = $taskOldConsole
    Pop-Location
}
