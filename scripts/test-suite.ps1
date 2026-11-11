[CmdletBinding()]
param(
    [ValidateSet('rapida', 'motor', 'integracao', 'relatorios', 'indices', 'frontend', 'completa')]
    [string]$Suite = 'rapida',
    [switch]$Listar,
    [switch]$Coletar
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projeto = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $projeto 'backend'
$frontend = Join-Path $projeto 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

# Cada arquivo pertence a uma familia. A suite completa descobre todos os testes.
# O inventario abaixo detecta arquivos novos ainda sem familia definida.
$familias = [ordered]@{
    motor = @(
        'test_civil_3.py', 'test_civil_4.py', 'test_civil_5.py', 'test_civil_6.py',
        'test_correcao.py', 'test_descontos.py', 'test_honorarios_fazenda.py',
        'test_honorarios_isolados.py', 'test_honorarios_principais.py',
        'test_honorarios_proveito.py', 'test_honorarios_valor_certo.py',
        'test_inicio_juros.py', 'test_ipca_taxa_legal.py',
        'test_ipcae_mensal.py', 'test_juros.py', 'test_limites_civil_1.py',
        'test_multas_parcelas.py', 'test_novos_perfis.py',
        'test_ordem_parcelas.py', 'test_parcelas.py', 'test_perfis_ec136.py',
        'test_poupanca_deposito.py', 'test_preenchimento_serie.py',
        'test_selic_cjf.py', 'test_simplificado.py'
    )
    integracao = @(
        'test_api.py', 'test_calculos_salvos.py', 'test_codex_integration.py',
        'test_codex_service.py', 'test_desktop.py', 'test_importador_excel.py',
        'test_mcp_server.py', 'test_updates.py'
    )
    relatorios = @(
        'test_custas_paginacao.py', 'test_gerador_honorarios_anexo.py',
        'test_pdf.py', 'test_relatorios_padronizados.py'
    )
    indices = @(
        'test_fontes_oficiais.py', 'test_index_data.py', 'test_indices_historicos.py',
        'test_publisher_key_path.py'
    )
}

if ($Listar) {
    Write-Host 'rapida       Regressoes essenciais do backend e testes do frontend'
    foreach ($nome in $familias.Keys) {
        Write-Host ('{0,-12} {1} arquivos de teste do backend' -f $nome, $familias[$nome].Count)
    }
    Write-Host 'frontend     Todos os testes Node do frontend'
    Write-Host 'completa     Todos os testes do backend e do frontend'
    exit 0
}

if ($Coletar -and $Suite -eq 'frontend') {
    throw 'A coleta sem execucao esta disponivel apenas para o backend.'
}

$executarBackend = $Suite -ne 'frontend'
$executarFrontend = $Suite -in @('rapida', 'frontend', 'completa') -and -not $Coletar

if ($executarFrontend) {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'npm.cmd nao foi encontrado no PATH.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules') -PathType Container)) {
        throw 'Dependencias do frontend ausentes. Execute npm install em frontend.'
    }
}

if ($executarBackend) {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Ambiente Python ausente: $python. Instale backend/[dev] antes de executar."
    }

    $atribuidos = @(
        foreach ($nome in $familias.Keys) {
            foreach ($arquivo in $familias[$nome]) { $arquivo }
        }
    )
    $existentes = @(Get-ChildItem -LiteralPath (Join-Path $backend 'tests') -Filter 'test_*.py' -File |
        ForEach-Object { $_.Name })
    $semFamilia = @($existentes | Where-Object { $_ -notin $atribuidos })
    $inexistentes = @($atribuidos | Where-Object { $_ -notin $existentes })
    $repetidos = @($atribuidos | Group-Object | Where-Object { $_.Count -gt 1 } |
        ForEach-Object { $_.Name })
    if ($semFamilia.Count -or $inexistentes.Count -or $repetidos.Count) {
        throw ('Inventario de testes inconsistente. Sem familia: [{0}]; inexistentes: [{1}]; repetidos: [{2}].' -f
            ($semFamilia -join ', '), ($inexistentes -join ', '), ($repetidos -join ', '))
    }
}

$resultados = @()
$runRoot = Join-Path $projeto ('build\test-suite\' + (Get-Date -Format 'yyyyMMddTHHmmssfff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))

if ($executarBackend) {
    New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
    $alvos = @(switch ($Suite) {
        'rapida' {
            @(
                'tests/test_correcao.py', 'tests/test_juros.py',
                'tests/test_civil_3.py', 'tests/test_limites_civil_1.py',
                'tests/test_preenchimento_serie.py', 'tests/test_fontes_oficiais.py'
            )
        }
        'completa' { @('tests') }
        default { @($familias[$Suite] | ForEach-Object { 'tests/' + $_ }) }
    })

    $opcoes = @('-X', 'utf8', '-m', 'pytest', '-q', '-ra', '--strict-config',
        '-o', 'faulthandler_timeout=60', '--basetemp', (Join-Path $runRoot 'pytest-temp'))
    if ($Coletar) { $opcoes += '--collect-only' }
    Write-Host "Backend: $Suite ($($alvos.Count) alvo(s))"
    Push-Location $backend
    try {
        & $python @opcoes @alvos
        $resultados += [pscustomobject]@{ Etapa = 'backend'; Codigo = $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

if ($executarFrontend) {
    Write-Host 'Frontend: npm test'
    Push-Location $frontend
    try {
        & npm.cmd test
        $resultados += [pscustomobject]@{ Etapa = 'frontend'; Codigo = $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

foreach ($resultado in $resultados) {
    Write-Host ("{0}: saida {1}" -f $resultado.Etapa, $resultado.Codigo)
}
if ($executarBackend) { Write-Host "Temporarios isolados: $runRoot" }
if (@($resultados | Where-Object { $_.Codigo -ne 0 }).Count) { exit 1 }
exit 0
