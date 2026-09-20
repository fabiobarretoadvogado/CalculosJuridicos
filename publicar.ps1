param(
    [string]$Repositorio = '',
    [string]$Versao = '',
    [string]$Notas = '',
    [string]$Python = '',
    [switch]$Preparar
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$taskProject = $PSScriptRoot
if (-not $Python) {
    $taskVenv = Join-Path $taskProject 'backend\.venv\Scripts\python.exe'
    $Python = if (Test-Path -LiteralPath $taskVenv) { $taskVenv } else { 'python' }
}
$taskOldPythonPath = $env:PYTHONPATH
$taskOldBytecode = $env:PYTHONDONTWRITEBYTECODE
Push-Location -LiteralPath $taskProject
try {
    $env:PYTHONPATH = Join-Path $taskProject 'backend'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $taskConfiguration = Join-Path $taskProject 'publisher.json'
    if (Test-Path -LiteralPath $taskConfiguration) {
        $taskStored = Get-Content -LiteralPath $taskConfiguration -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $Repositorio) { $Repositorio = $taskStored.repository }
    }
    if (-not $Repositorio -and -not $Preparar) {
        throw 'Informe -Repositorio no formato conta/nome. Nenhum arquivo foi enviado.'
    }

    $taskPublisher = Join-Path $taskProject 'scripts\publisher.py'
    $taskResolvedJson = & $Python -B $taskPublisher version ('--version=' + $Versao)
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível determinar a edição solicitada.' }
    $taskResolved = $taskResolvedJson | ConvertFrom-Json
    $Versao = $taskResolved.version
    $taskDisplayVersion = $taskResolved.display_version

    if (-not $Preparar) {
        & $Python -B $taskPublisher preflight --repository $Repositorio --access public
        if ($LASTEXITCODE -ne 0) { throw 'O acesso ao repositório não foi confirmado.' }
    }
    & $Python -B $taskPublisher configure --repository $Repositorio --version $Versao --display-version $taskDisplayVersion --access public
    if ($LASTEXITCODE -ne 0) { throw 'A configuração da publicação foi interrompida.' }

    Push-Location -LiteralPath (Join-Path $taskProject 'backend')
    try {
        $taskBuildRoot = Join-Path $taskProject 'build'
        New-Item -ItemType Directory -Path $taskBuildRoot -Force | Out-Null
        $taskPytestTemp = Join-Path $taskBuildRoot ('pytest-publicacao-' + [guid]::NewGuid().ToString('N'))
        & $Python -B -m pytest -q --basetemp $taskPytestTemp
        if ($LASTEXITCODE -ne 0) { throw 'Os testes do cálculo falharam. Publicação interrompida.' }
    }
    finally { Pop-Location }

    & (Join-Path $taskProject 'build-installer.ps1') -Python $Python
    if ($LASTEXITCODE -ne 0) { throw 'O instalador não foi gerado.' }

    $taskOutput = Join-Path $taskProject ('instaladores\' + $Versao)
    $taskInstaller = Join-Path $taskOutput ('CalculosJuridicos-Setup-' + $Versao + '-x64.exe')
    $taskNotes = Join-Path $taskOutput 'Notas-da-versao.md'
    if ($Notas) {
        Copy-Item -LiteralPath $Notas -Destination $taskNotes -Force
    }
    else {
        Copy-Item -LiteralPath (Join-Path $taskProject 'Notas-de-publicacao.md') -Destination $taskNotes -Force
    }
    if ($Repositorio) {
        & $Python -B $taskPublisher manifest --repository $Repositorio --installer $taskInstaller --output (Join-Path $taskOutput 'update.json') --notes $taskNotes
        if ($LASTEXITCODE -ne 0) { throw 'A assinatura da atualização não foi confirmada.' }
    }
    if ($Preparar) {
        Write-Host ('Preparação concluída: ' + $taskOutput + '. Nenhum arquivo foi enviado.')
        return
    }
    & $Python -B $taskPublisher publish --repository $Repositorio --output $taskOutput --notes $taskNotes --access public
    if ($LASTEXITCODE -ne 0) { throw 'A publicação não foi concluída. Um eventual rascunho foi preservado.' }
}
finally {
    $env:PYTHONPATH = $taskOldPythonPath
    $env:PYTHONDONTWRITEBYTECODE = $taskOldBytecode
    Pop-Location
}
