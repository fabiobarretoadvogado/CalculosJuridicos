param(
    [string]$Repositorio = '',
    [string]$Pacote = '',
    [string]$Python = '',
    [switch]$Preparar
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskProject = $PSScriptRoot
if (-not $Python) { $Python = Join-Path $taskProject 'backend\.venv\Scripts\python.exe' }
$taskPublisher = Join-Path $taskProject 'scripts\publisher_indices.py'
if (-not $Repositorio) {
    $taskConfiguration = Get-Content -LiteralPath (Join-Path $taskProject 'publisher.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $Repositorio = $taskConfiguration.repository
}
if (-not $Pacote) {
    $taskPrepared = & $Python -B $taskPublisher prepare --repository $Repositorio
    if ($LASTEXITCODE -ne 0) { throw 'O pacote de índices não pôde ser preparado e validado.' }
    $Pacote = ($taskPrepared | ConvertFrom-Json).directory
}
if ($Preparar) {
    Write-Host ('Pacote de índices preparado: ' + $Pacote)
    return
}
& $Python -B $taskPublisher publish --repository $Repositorio --output $Pacote
if ($LASTEXITCODE -ne 0) { throw 'A publicação dos índices não foi concluída. Um eventual rascunho foi preservado.' }
