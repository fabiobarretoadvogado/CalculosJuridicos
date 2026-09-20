import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { after, before, test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

let server;
let CalculoContext;
let ResultadoPrincipal;
let Processamento;
let Importacao;
let Layout;
let HonorariosPrincipaisForm;
let DestaquesForm;
let HonorariosSucumbenciais;
let prepararOperacaoDivida;
let EscalonamentoFazendaForm;
let EscalonamentoFazendaResultado;
let escalonamentoInicial;
let fixacaoHonorarios;
let montarHonorariosIsolados;
let limiteHonorariosAutonomos;
let HonorariosValorCertoCampos;
let HonorariosValorCertoResultado;
let DescontosForm;
let UpdateStatusView;

before(async () => {
  server = await createServer({
    server: { middlewareMode: true }, appType: 'custom',
    // Rendering tests isolate network/download actions; the real API is checked in the browser.
    plugins: [{
      name: 'isolated-render-api', enforce: 'pre',
      load(id) {
        if (!id.replaceAll('\\', '/').endsWith('/src/services/api.ts')) return;
        return ['executarCalculo', 'executarHonorariosProveito', 'executarHonorariosIsolados', 'exportarPdfHonorarios', 'exportarPdfHonorariosIsolados', 'obterCriterios', 'obterCoberturaHonorarios', 'mensagemErro', 'exportarPdf', 'exportarExcel', 'exportarCsv', 'importarExcel', 'obterTemplateModelo']
          .map(name => `export function ${name}() { throw new Error('Unexpected IO in render test'); }`).join('\n');
      },
    }],
  });
  ({ CalculoContext } = await server.ssrLoadModule('/src/contexts/CalculoContextBase.ts'));
  ({ ResultadoPrincipal } = await server.ssrLoadModule('/src/components/ResultadoPrincipal.tsx'));
  ({ Processamento } = await server.ssrLoadModule('/src/pages/Processamento.tsx'));
  ({ Importacao } = await server.ssrLoadModule('/src/pages/Importacao.tsx'));
  ({ Layout } = await server.ssrLoadModule('/src/components/Layout.tsx'));
  ({ HonorariosPrincipaisForm, DestaquesForm } = await server.ssrLoadModule('/src/components/HonorariosPrincipaisForm.tsx'));
  ({ HonorariosSucumbenciais } = await server.ssrLoadModule('/src/pages/HonorariosSucumbenciais.tsx'));
  ({ prepararOperacaoDivida } = await server.ssrLoadModule('/src/utils/honorariosProveito.ts'));
  ({ EscalonamentoFazendaForm, EscalonamentoFazendaResultado } = await server.ssrLoadModule('/src/components/EscalonamentoFazendaHonorarios.tsx'));
  ({ escalonamentoInicial, fixacaoHonorarios } = await server.ssrLoadModule('/src/utils/honorariosFazenda.ts'));
  ({ montarHonorariosIsolados, limiteHonorariosAutonomos } = await server.ssrLoadModule('/src/utils/honorariosIsolados.ts'));
  ({ HonorariosValorCertoCampos, HonorariosValorCertoResultado } = await server.ssrLoadModule('/src/components/HonorariosValorCerto.tsx'));
  ({ DescontosForm } = await server.ssrLoadModule('/src/components/DescontosForm.tsx'));
  ({ UpdateStatusView } = await server.ssrLoadModule('/src/components/UpdateStatus.tsx'));
});

after(async () => { await server?.close(); });

test('atualizador mantém uma ação visível em todos os estados úteis', () => {
  const info = { nome: 'Cálculos Jurídicos', versao: '2026.9.20.6', edicao: '1.06', empacotado: true, atualizacoes_configuradas: true, repositorio: 'conta/projeto', acesso: 'public' };
  const props = { info, atualizacao: null, erro: '', onConsultar() {}, onAtualizar() {} };
  const atualizado = renderToStaticMarkup(createElement(UpdateStatusView, { ...props, estado: 'atualizado' }));
  assert.match(atualizado, /Versão 1\.06/);
  assert.match(atualizado, /Verificar atualização/);
  const disponivel = renderToStaticMarkup(createElement(UpdateStatusView, { ...props, estado: 'disponivel', atualizacao: { disponivel: true, versao_atual: info.versao, nova_edicao: '1.07' } }));
  assert.match(disponivel, /Atualizar para 1\.07/);
  const indisponivel = renderToStaticMarkup(createElement(UpdateStatusView, { ...props, estado: 'indisponivel', erro: 'Sem conexão' }));
  assert.match(indisponivel, /Tentar novamente/);
  assert.match(indisponivel, /role="alert"/);
});

test('descontos permitem poupança bancária independente sem marco de juros moratórios', () => {
  const operacao = { perfil: 'poupanca_deposito_v1', criterio_inicio_juros: 'citacao', data_inicial_juros: null,
    itens: [{ numero: 1, aplicar: true, descricao: 'Depósito judicial', data: '2025-12-31', valor: '5845.82', encargos_sem_atualizacao: '531.89' }] };
  const html = renderToStaticMarkup(createElement(DescontosForm, { operacao, perfilPrincipal: 'selic_cjf_v1', dataBase: '2026-09-01', onChange() {} }));
  assert.match(html, /value="poupanca_deposito_v1" selected=""/);
  assert.match(html, /Poupança — remuneração da conta/);
  assert.match(html, /aniversários completos/);
  assert.match(html, /Data do depósito/);
  assert.match(html, /Parte fora da conta, sem remuneração/);
  assert.match(html, /5\.313,93/);
  assert.doesNotMatch(html, /id="descontos-inicio-juros"|id="descontos-data-juros"/);
});

test('pagamentos selecionáveis conservam os campos e exigem data/valor somente quando ativos', () => {
  const operacao = { perfil: 'selic_cjf_v1', criterio_inicio_juros: 'vencimento', data_inicial_juros: null, itens: [
    { numero: 1, descricao: 'Pagamento bruto', data: '2025-12-31', valor: '5845.82', encargos_sem_atualizacao: '45.82' },
    { numero: 2, aplicar: false, descricao: 'Em conferência', data: null, valor: null },
  ] };
  const html = renderToStaticMarkup(createElement(DescontosForm, { operacao, perfilPrincipal: 'selic_cjf_v1', dataBase: '2026-09-01', onChange() {} }));
  assert.match(html, /1 de 2 selecionados/);
  assert.match(html, /aria-label="Abater desconto 1"[^>]*checked=""/);
  assert.doesNotMatch(html, /aria-label="Abater desconto 2"[^>]*checked=""/);
  assert.match(html, /id="desconto-data-1"[^>]*required=""/);
  assert.doesNotMatch(html, /id="desconto-data-2"[^>]*(required|max|min)=/);
  assert.match(html, /id="desconto-base-1"[^>]*readOnly=""[^>]*value="5\.800,00"/);
  const changes = [];
  const tree = DescontosForm({ operacao, perfilPrincipal: 'selic_cjf_v1', dataBase: '2026-09-01', onChange(value) { changes.push(value); } });
  function find(node, match) {
    if (!node || typeof node !== 'object') return undefined;
    if (match(node)) return node;
    return [node.props?.children].flat(Infinity).map(n => find(n, match)).find(Boolean);
  }
  find(tree, node => node.props?.['aria-label'] === 'Abater desconto 1').props.onChange({ target: { checked: false } });
  assert.deepEqual(changes[0].itens[0], { ...operacao.itens[0], aplicar: false });
  assert.deepEqual(changes[0].itens[1], operacao.itens[1]);
  find(tree, node => node.props?.id === 'desconto-encargos-1').props.onChange({ target: { value: '20' } });
  assert.equal(changes[1].itens[0].encargos_sem_atualizacao, '20');
  assert.equal(changes[1].itens[0].valor, '5845.82');
});

test('valor certo tem fixação e juros independentes com campos exclusivos de cada regime', () => {
  for (const juros of ['simples', 'taxa_legal', 'sem_juros']) {
    const config = { data_fixacao: '2026-01-15', indice: 'ipca', juros, data_inicio_juros: '2026-03-03', percentual_mensal: '1', contagem_mes_cheio: false };
    const html = renderToStaticMarkup(createElement(HonorariosValorCertoCampos, { config, dataBase: '2026-08-31', onChange() {} }));
    assert.match(html, /id="valor-certo-data-fixacao"[^>]*required=""/);
    assert.match(html, /trânsito em julgado/);
    assert.equal(html.includes('id="valor-certo-data-juros"'), juros !== 'sem_juros');
    assert.equal(html.includes('id="valor-certo-percentual-mensal"'), juros === 'simples');
    assert.equal(html.includes('id="valor-certo-contagem"'), juros === 'simples');
    if (juros === 'taxa_legal') assert.match(html, /min="2026-01-15"/);
    assert.deepEqual(config, { data_fixacao: '2026-01-15', indice: 'ipca', juros, data_inicio_juros: '2026-03-03', percentual_mensal: '1', contagem_mes_cheio: false });
  }
});

test('payload conserva encargos preenchidos sem enviar juros ou taxas ocultas', () => {
  const dados = { data_base: '2026-08-31' }, campos = { valor_certo: '1500', valor_causa: '1000', indice: 'ipca', data_protocolo: '2026-01-01' };
  const original = { data_fixacao: '2026-01-15', indice: 'ipcae', juros: 'taxa_legal', data_inicio_juros: '2026-03-03', percentual_mensal: '1', contagem_mes_cheio: true };
  const legal = montarHonorariosIsolados('valor_certo', dados, campos, [], false, '20', {}, original);
  assert.equal(legal.encargos_valor_certo.percentual_mensal, null);
  assert.equal(legal.encargos_valor_certo.contagem_mes_cheio, false);
  assert.equal(legal.encargos_valor_certo.data_inicio_juros, '2026-03-03');
  const sem = montarHonorariosIsolados('valor_certo', dados, campos, [], false, '20', {}, { ...original, juros: 'sem_juros' });
  assert.equal(sem.encargos_valor_certo.data_inicio_juros, null);
  assert.equal(sem.encargos_valor_certo.percentual_mensal, null);
  assert.ok(!('encargos_valor_certo' in montarHonorariosIsolados('valor_causa', dados, campos, [], false, '20', {}, original)));
  assert.ok(!('encargos_valor_certo' in montarHonorariosIsolados('valor_certo', dados, campos, [], false, '20', {}, null)));
  assert.equal(original.percentual_mensal, '1');
  assert.equal(original.contagem_mes_cheio, true);
});

test('cobertura do valor fixado acompanha correção e Taxa Legal sem depender das dívidas ocultas', () => {
  const coverage = { ipcae: { data_base_maxima: '2026-08-31' }, ipca: { data_base_maxima: '2026-07-31' }, taxa_legal: { data_base_maxima: '2026-06-30' } };
  const config = { indice: 'ipca', juros: 'simples' };
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipcae', coverage, { data_base_maxima: '2020-01-01' }, null, false, config), '2026-07-31');
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipcae', coverage, null, null, false, { ...config, juros: 'taxa_legal' }), '2026-06-30');
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipcae', coverage, null, null, true, { ...config, indice: 'ipcae' }), '2026-08-31');
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipcae', coverage, null, null, false, null), undefined);
});

test('resultado do valor certo discrimina correção, juros e datas sem fórmula de dívida', () => {
  const componente = { data_inicial: '2026-03-03', data_final: '2026-08-30', base_calculo: '1520', fator_acumulado: null, taxa_acumulada_percentual: '3.123456', valor: '47.48' };
  const r = { atualizacao_valor_certo: { valor_bruto: '1500', correcao_monetaria: '20', juros_mora: '47.48', total_parcela: '1567.48', componentes: { juros: componente }, memoria_correcao: [], memoria_juros: [] }, premissas: { criterios: ['EXEMPLO'], metodologia: [], fontes: {} } };
  const html = renderToStaticMarkup(createElement(HonorariosValorCertoResultado, { resultado: r }));
  for (const texto of ['Valor fixado', 'Correção monetária', 'Juros de mora', 'Honorários atualizados', '03/03/2026', '30/08/2026', '3,123456%']) assert.ok(html.includes(texto));
  assert.doesNotMatch(html, /Dívida correta|Proveito econômico|Valor da causa/);
});

test('aba Honorários permite três bases e não exige dívidas no valor certo ou causa', () => {
  for (const base of ['proveito_economico', 'valor_causa', 'valor_certo']) {
    const html = renderToStaticMarkup(createElement(HonorariosSucumbenciais, { baseInicial: base }));
    assert.match(html, /Equidade · valor certo/);
    assert.match(html, /Valor da causa atualizado/);
    assert.match(html, new RegExp('value="' + base + '" selected=""'));
    assert.ok(html.indexOf('Partes e observações') < html.indexOf('Dados do cálculo'));
    if (base === 'proveito_economico') {
      assert.match(html, /Dívida originalmente exigida/);
      assert.match(html, /Dívida correta/);
      assert.match(html, /id="correta-extincao-integral"/);
      assert.match(html, /Dívida integralmente extinta/);
      assert.doesNotMatch(html, /id="original-extincao-integral"/);
    } else {
      assert.doesNotMatch(html, /Dívida originalmente exigida|Dívida correta/);
    }
    if (base === 'valor_causa') {
      assert.match(html, /Valor da causa no protocolo/);
      assert.match(html, /Data do protocolo/);
  assert.match(html, /IPCA-E · IBGE \/ SGS 7478/);
      assert.match(html, /IPCA · IBGE/);
      assert.match(html, /id="honorarios-fixacao"/);
      assert.doesNotMatch(html, /id="honorarios-valor-certo"/);
    } else if (base === 'valor_certo') {
      assert.match(html, /Valor fixado dos honorários/);
      assert.match(html, /Data da fixação/);
      assert.match(html, /Trânsito em julgado \/ início dos juros/);
      assert.match(html, /Taxa Legal · BCB/);
      assert.match(html, /Juros simples \(% ao mês\)/);
      assert.match(html, /id="valor-certo-data-fixacao"[^>]*required=""/);
      assert.match(html, /id="valor-certo-data-juros"[^>]*required=""/);
      assert.doesNotMatch(html, /id="honorarios-percentual"|id="honorarios-fixacao"|id="honorarios-protocolo"|id="honorarios-indice"|id="honorarios-salario-minimo"/);
    }
  }
});

test('extinção integral envia dívida correta zerada sem perder os itens preenchidos na tela', () => {
  const operacao = {
    perfil: 'selic_ipcae_poupanca_v1', criterio_inicio_juros: 'data_fixa',
    data_inicial_juros: '2025-01-01', multa_moratoria_percentual: '10',
    extincao_integral: true,
    parcelas: [{ numero: 1, historico: 'Item preservado', data_origem: '2024-01-01', valor: '1000' }],
  };

  const enviada = prepararOperacaoDivida(operacao);

  assert.equal(enviada.extincao_integral, true);
  assert.deepEqual(enviada.parcelas, []);
  assert.equal(enviada.data_inicial_juros, null);
  assert.equal(enviada.multa_moratoria_percentual, '0');
  assert.equal(operacao.parcelas[0].valor, '1000');
});

test('montagem isolada envia apenas campos aplicáveis, sem perder valores ao alternar', () => {
  const config = { valor_causa: '10000', data_protocolo: '2025-09-01', indice: 'ipca', valor_certo: '1500' };
  const dados = { data_base: '2026-08-31', processo: '' };
  const custas = [{ numero: 1, nome: 'Custa', data: '2026-01-01', valor: '250' }];
  const anterior = structuredClone(config);
  const faixas = escalonamentoInicial();
  const certo = montarHonorariosIsolados('valor_certo', dados, config, custas, true, '20', faixas);
  assert.equal(certo.valor_certo, '1500');
  assert.equal(certo.percentual_sentenca, null);
  assert.equal(certo.escalonamento_fazenda, null);
  assert.ok(!('valor_causa' in certo) && !('data_protocolo' in certo) && !('indice' in certo));
  const causa = montarHonorariosIsolados('valor_causa', dados, config, custas, false, '20', faixas);
  assert.equal(causa.valor_causa, '10000');
  assert.equal(causa.indice, 'ipca');
  assert.equal(causa.percentual_sentenca, '20');
  assert.ok(!('valor_certo' in causa) && !('divida_original' in causa));
  const publica = montarHonorariosIsolados('valor_causa', dados, config, custas, true, '20', faixas);
  assert.equal(publica.percentual_sentenca, null);
  assert.deepEqual(publica.escalonamento_fazenda, faixas);
  assert.deepEqual(config, anterior);
  certo.custas_despesas[0].valor = '300';
  assert.equal(custas[0].valor, '250');
});

test('cobertura dos honorários isolados depende só do índice e das custas aplicáveis', () => {
  const cobertura = { ipcae: { data_base_maxima: '2026-08-31' }, ipca: { data_base_maxima: '2026-07-31' } };
  const original = { data_base_maxima: '2025-10-31', data_base_maxima_ipcae: '2026-08-31' };
  const correta = { data_base_maxima: '2025-09-30' };
  assert.equal(limiteHonorariosAutonomos('valor_causa', 'ipcae', cobertura, original, correta, false), '2026-08-31');
  assert.equal(limiteHonorariosAutonomos('valor_causa', 'ipca', cobertura, original, correta, true), '2026-07-31');
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipca', cobertura, original, correta, false), undefined);
  assert.equal(limiteHonorariosAutonomos('valor_certo', 'ipca', cobertura, original, correta, true), '2026-08-31');
  assert.equal(limiteHonorariosAutonomos('proveito_economico', 'ipcae', cobertura, original, correta, false), '2025-09-30');
});

test('honorários autônomos preservam percentual único como padrão e oferecem faixas', () => {
  const html = renderToStaticMarkup(createElement(HonorariosSucumbenciais));
  assert.match(html, /Faixas · Fazenda Pública \(art\. 85\)/);
  assert.match(html, /value="percentual" selected=""/);
  assert.match(html, /Percentual fixado na sentença/);
  assert.doesNotMatch(html, /id="honorarios-salario-minimo"/);
});

test('faixas exigem salário e marco e preservam as cinco bandas legais', () => {
  const config = escalonamentoInicial();
  assert.deepEqual(config.percentuais_faixas, ['10', '8', '5', '3', '1']);
  assert.equal(config.salario_minimo, '');
  assert.equal(config.data_decisao, '');
  const html = renderToStaticMarkup(createElement(EscalonamentoFazendaForm, { config, onChange: () => {} }));
  assert.match(html, /Salário mínimo nessa data/);
  assert.match(html, /id="honorarios-salario-minimo"[^>]*required=""/);
  assert.match(html, /id="honorarios-data-decisao"[^>]*required=""/);
  assert.equal((html.match(/id="honorarios-faixa-\d"/g) || []).length, 5);
  for (const [i, min, max] of [[1,10,20],[2,8,10],[3,5,8],[4,3,5],[5,1,3]]) {
    assert.match(html, new RegExp(`id="honorarios-faixa-${i}"[^>]*min="${min}"[^>]*max="${max}"`));
  }
  assert.match(html, /confirme ou ajuste conforme a decisão/);
  assert.match(html, /somente|excedente/);
  const liquidacao = renderToStaticMarkup(createElement(EscalonamentoFazendaForm, { config: { ...config, marco: 'decisao_liquidacao' }, onChange: () => {} }));
  assert.match(liquidacao, /Data da decisão de liquidação/);
  assert.doesNotMatch(liquidacao, /max="2026-/);
});

test('alternar fixação não mistura percentuais nem modifica o formulário anterior', () => {
  const config = { ...escalonamentoInicial(), salario_minimo: '1518', data_decisao: '2025-09-09' };
  const antes = structuredClone(config);
  const publica = fixacaoHonorarios(true, '20', config);
  assert.equal(publica.percentual_sentenca, null);
  assert.deepEqual(publica.escalonamento_fazenda, config);
  publica.escalonamento_fazenda.percentuais_faixas[0] = '15';
  assert.deepEqual(config, antes);
  assert.deepEqual(fixacaoHonorarios(false, '20', config), { percentual_sentenca: '20', escalonamento_fazenda: null });
});

test('resultado por faixas tem cabeçalho único e taxas com até quatro casas', () => {
  const r = { ...escalonamentoInicial(), salario_minimo: '1000', data_decisao: '2026-09-09', base_calculo: '100', valor_total: '10', fonte: 'https://www.planalto.gov.br/',
    faixas: [{ ordem: 1, limite_inferior_salarios_minimos: '0', limite_salarios_minimos: '200', percentual_aplicado: '10.1234', valor_incidente: '100', valor: '10.12' },
      { ordem: 5, limite_inferior_salarios_minimos: '100000', limite_salarios_minimos: null, percentual_aplicado: '1', valor_incidente: '0', valor: '0' }] };
  const html = renderToStaticMarkup(createElement(EscalonamentoFazendaResultado, { resultado: r }));
  assert.equal((html.match(/<thead>/g) || []).length, 1);
  assert.match(html, /Até 200 SM/);
  assert.match(html, /Acima de 100\.000 SM/);
  assert.match(html, /10,1234%/);
  assert.match(html, /Não alcançada/);
  assert.match(html, /09\/09\/2026/);
  assert.match(html, /Custas e despesas são somadas separadamente/);
});

function render(component, resultado = null, overrides = {}) {
  const entrada = {
    honorarios: { aplicar: false, base: 'proveito_economico', percentual: null, valor_causa: null, data_protocolo: null, indice: 'ipcae', valor_certo: null },
    cumprimento: { aplicar_multa: false, aplicar_honorarios: false, destacar_contratuais: false, percentual_contratuais: null, base_contratuais: 'credito_parte' },
    perfil: 'selic_cjf_v1', dados_gerais: { data_base: '2026-08-31', processo: 'TESTE', criterio_inicio_juros: 'vencimento' },
    parcelas: [{ numero: 1, historico: 'Parcela de teste', data_vencimento: '2025-09-01', valor_bruto: '100', valor_pago_na_data: '0' }],
    custas_despesas: [],
  };
  return renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: ['/processamento'] },
    createElement(CalculoContext.Provider, { value: {
      state: { honorariosSucumbenciais: entrada.honorarios, cumprimentoSentenca: entrada.cumprimento, perfil: entrada.perfil, parcelas: entrada.parcelas, descontos: { perfil: null, criterio_inicio_juros: 'vencimento', data_inicial_juros: null, itens: [] }, custasDespesas: [], resultado, ...overrides, dadosGerais: { ...entrada.dados_gerais, ...overrides.dadosGerais } },
      dispatch: () => {}, buildCalculoJudicial: () => entrada,
    } }, createElement(component))));
}

const resultado = {
  dados_gerais: { data_base: '2026-08-31', processo: 'TESTE', observacoes: '' },
  resumo: { principal_apurado: '100.00', totais_componentes: { selic: '12.00' }, custas: '21.00', total_atualizado: '133.00' },
  parcelas: [{ numero: 1, historico: 'Parcela de teste', data_vencimento: '2025-09-01', valor_apurado: '100.00', total_parcela: '112.00',
    componentes: { selic: { data_inicial: '2025-09-01', data_final: '2026-08-31', base_calculo: '100.00', fator_acumulado: null, taxa_acumulada_percentual: '12.0000', valor: '12.00' } } }],
  custas_despesas: [{ numero: 1, nome: 'Taxa de teste', data: '2025-09-01', valor_original: '20.00', fator_ipcae: '1.05', correcao_monetaria: '1.00', valor_atualizado: '21.00', memoria: [] }],
  memoria_mensal: [], alertas: [],
  premissas: { entrada: { perfil: 'selic_cjf_v1' }, criterios: ['SELIC'], metodologia: ['Atualização mensal'], fontes: {} },
};

test('Civil 1 oferece datas independentes sem limitar juros à correção', () => {
  const html = render(Processamento, null, { perfil: 'ipca_taxa_legal_v1', dadosGerais: { criterio_inicio_juros: 'por_parcela' } });
  assert.match(html, />Civil 1</);
  assert.match(html, /Início da correção/);
  assert.match(html, /Pode ser anterior à correção/);
  assert.match(html, /Taxa Legal: taxas oficiais do Banco Central/);
  assert.doesNotMatch(html, /respeitado o vencimento da parcela/);
});

test('Civil 2 oferece IPCA e juros simples de 1% ao mês com datas independentes', () => {
  const html = render(Processamento, null, { perfil: 'civil_2_v1', dadosGerais: { criterio_inicio_juros: 'por_parcela' } });
  assert.match(html, />Civil 2</);
  assert.match(html, /Início da correção/);
  assert.match(html, /Pode ser anterior à correção/);
  assert.match(html, /Juros de mora: 1% ao mês, de forma simples/);
  assert.match(html, /os juros não são capitalizados/);
  assert.doesNotMatch(html, /respeitado o vencimento da parcela/);
});

test('resultado SELIC distingue referência mensal e última competência aplicada', () => {
  const r = structuredClone(resultado);
  r.custas_despesas = [];
  r.premissas.data_referencia_selic = '2026-08-01';
  r.premissas.ultima_competencia_selic = '2026-07';
  const html = render(ResultadoPrincipal, r);
  assert.match(html, /Data-base SELIC 01\/08\/2026/);
  assert.match(html, /Último índice aplicado: 07\/2026/);
  assert.match(html, /não representa atualização diária/);
  assert.doesNotMatch(html, /Data-base 31\/08\/2026|Data final das demais operações/);
  assert.equal(r.dados_gerais.data_base, '2026-08-31');
});

test('SELIC preserva a data final das outras operações e não inventa último índice', () => {
  const r = structuredClone(resultado);
  r.premissas.data_referencia_selic = '2026-08-01';
  r.premissas.ultima_competencia_selic = null;
  const html = render(ResultadoPrincipal, r);
  assert.match(html, /Último índice aplicado: nenhum/);
  assert.match(html, /Data final das demais operações: 31\/08\/2026/);
  assert.match(html, /Taxa de teste/);
  const form = render(Processamento);
  assert.match(form, /Data-base SELIC: 01\/08\/2026/);
  assert.match(form, /Custas e demais operações usam a data final informada/);
  assert.match(form, /id="data-base"[^>]*value="2026-08-31"/);
});

test('resultado IPCA e Taxa Legal mostra períodos independentes e taxa de seis casas', () => {
  const r = structuredClone(resultado);
  r.premissas.entrada.perfil = 'ipca_taxa_legal_v1';
  r.resumo.totais_componentes = { ipca: '-1.55', taxa_legal: '216.19' };
  r.parcelas[0].componentes = {
    ipca: { data_inicial: '2026-08-28', data_final: '2026-08-30', base_calculo: '5000', fator_acumulado: '0.999689874', taxa_acumulada_percentual: null, valor: '-1.55' },
    taxa_legal: { data_inicial: '2026-02-02', data_final: '2026-08-30', base_calculo: '4998.449370', fator_acumulado: null, taxa_acumulada_percentual: '4.325078', valor: '216.19' },
  };
  const html = render(ResultadoPrincipal, r);
  assert.match(html, /4,325078%/);
  assert.match(html, /02\/02\/2026 a 30\/08\/2026/);
  assert.match(html, /28\/08\/2026 a 30\/08\/2026/);
  assert.match(html, /Correção desde/);
  assert.match(html, /sem SELIC integral adicional/);
});

test('menu contém somente as duas categorias renomeadas', () => {
  const html = render(() => createElement(Layout, null, 'Conteúdo'));
  const nav = html.match(/<nav\b[^>]*>([\s\S]*?)<\/nav>/)[1];
  assert.equal((nav.match(/<a\b/g) || []).length, 2);
  assert.match(nav, /Principal e honorários/);
  assert.match(nav, />Honorários</);
  assert.doesNotMatch(nav, /Resultado e PDF|Dados do cálculo|Honorários sucumbenciais/);
});

test('antes de calcular não há resultado nem exportação', () => {
  assert.equal(render(ResultadoPrincipal), '');
  const html = render(Processamento);
  assert.doesNotMatch(html, /principal-result|Baixar PDF/);
});

test('parcelas vazias usam o mesmo aviso compacto das custas, descontos e honorários', async () => {
  const html = render(Processamento, null, { parcelas: [] });
  const avisos = [...html.matchAll(/<div class="costs-empty">([\s\S]*?)<\/div>/g)].map(match => match[1]);
  assert.equal(avisos.length, 4);
  for (const aviso of avisos) {
    assert.match(aviso, /width="20" height="20"/);
    assert.match(aviso, /<span>[^<]+<\/span>/);
  }
  assert.match(avisos[0], /Adicione a primeira parcela ou importe uma planilha/);
  assert.match(avisos[2], /Honorários sucumbenciais não incluídos/);
  assert.match(avisos[3], /Nenhuma custa ou despesa informada/);
  assert.doesNotMatch(html, /class="empty-parcels"/);
  const css = await readFile(new URL('../src/index.css', import.meta.url), 'utf8');
  assert.match(css, /\.costs-empty\s*\{[^}]*display:\s*flex;[^}]*min-height:\s*52px;[^}]*padding:\s*12px 14px;/);
  assert.doesNotMatch(css, /\.processamento-page \.empty-parcels/);
});

test('descontos aparecem após parcelas e antes das custas, sem contorno adicional', () => {
  const html = render(Processamento);
  assert.ok(html.indexOf('id="parcelas-titulo"') < html.indexOf('id="descontos-titulo"'));
  assert.ok(html.indexOf('id="descontos-titulo"') < html.indexOf('id="principal-custas-titulo"'));
  assert.match(html, /Adicionar pagamento ou desconto/);
  assert.match(html, /Nenhum desconto informado/);
});

test('desconto tem descrição, data, valor e encargos independentes', () => {
  const html = render(Processamento, null, { descontos: { perfil: 'selic_ipcae_poupanca_v1', criterio_inicio_juros: 'data_fixa', data_inicial_juros: '2025-10-01', itens: [{ numero: 2, descricao: 'Pagamento posterior', data: '2025-09-15', valor: '20' }] } });
  for (const id of ['descontos-perfil', 'descontos-inicio-juros', 'descontos-data-juros', 'desconto-descricao-2', 'desconto-data-2', 'desconto-valor-2']) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(html, /Mesmo padrão das parcelas/);
  assert.match(html, /antes das custas/);
  assert.match(html, /Descontos informados/);
});

test('resultado concilia descontos, preserva parcelas e mostra memória própria', () => {
  const descontos = { ...resultado, custas_despesas: [], resumo: { ...resultado.resumo, custas: '0', total_atualizado: '22.40', principal_original: '20', totais_componentes: { selic: '2.40' } }, parcelas: [{ ...resultado.parcelas[0], historico: 'Crédito posterior', valor_bruto: '20', total_parcela: '22.40' }] };
  const html = render(ResultadoPrincipal, { ...resultado, descontos, resumo: { ...resultado.resumo, abatimentos: '22.40', total_atualizado: '110.60' } });
  assert.match(html, /Descontos atualizados/);
  assert.match(html, /Crédito posterior/);
  assert.match(html, /Critérios e memória dos descontos/);
  assert.match(html, /Parcelas atualizadas/);
  assert.match(html, /descontos abatidos/);
  assert.match(html, /110,60/);
});

test('ações de parcelas ficam juntas, sem outra seção expansível de importação', () => {
  const html = render(Processamento);
  const toolbar = html.match(/<div class="parcel-toolbar"[^>]*>([\s\S]*?)<\/div>/)[1];
  assert.equal((toolbar.match(/<button\b/g) || []).length, 2);
  assert.match(toolbar, /Adicionar parcela/);
  assert.match(toolbar, /Importar Excel/);
  assert.match(toolbar, /aria-expanded="false" aria-controls="importacao-parcelas"/);
  assert.match(html, /<section id="importacao-parcelas"[^>]* hidden=""/);
  assert.doesNotMatch(html, /<summary>Importar parcelas do Excel/);
});

test('painel aberto preserva modelo e seleção de planilha', () => {
  const html = render(() => createElement(Importacao, { aberto: true }));
  assert.doesNotMatch(html, / hidden=/);
  assert.match(html, /aria-labelledby="importacao-titulo"/);
  assert.match(html, /Baixar modelo/);
  assert.match(html, /type="file" accept=".xlsx"/);
  assert.match(html, /As parcelas serão adicionadas às já cadastradas/);
});

test('parcela mantém descrição, vencimento, valor, pagamento e saldo nessa ordem, sempre visíveis', () => {
  const html = render(Processamento);
  const campos = ['historico-1', 'vencimento-1', 'valor-1', 'pago-1', 'saldo-1'];
  const posicoes = campos.map(id => html.indexOf(`id="${id}"`));
  assert.ok(posicoes.every(posicao => posicao >= 0));
  assert.deepEqual(posicoes, [...posicoes].sort((a, b) => a - b));
  assert.doesNotMatch(html, /class="parcel-options"|Descrição, pagamento e juros/);
  assert.match(html, /id="saldo-1"[^>]*readonly=""[^>]*value="R\$ 100,00"/i);
});

test('saldo da parcela desconta o pagamento, aceita quitação e fica vazio antes de informar valor', () => {
  for (const [original, pago, esperado] of [['100.10', '20.20', '79,90'], ['100', '100', '0,00'], ['', '0', '—']]) {
    const html = render(Processamento, null, { parcelas: [{ numero: 1, historico: '', data_vencimento: '', valor_bruto: original, valor_pago_na_data: pago }] });
    const saldo = html.match(/<input\b[^>]*id="saldo-1"[^>]*>/)[0];
    assert.ok(saldo.includes(esperado), `Saldo esperado: ${esperado}`);
    assert.match(saldo, /readonly=""/i);
  }
});

test('cada parcela permite multa percentual opcional sem alterar o saldo anterior aos encargos', () => {
  const html = render(Processamento, null, { parcelas: [{ numero: 1, historico: '', data_vencimento: '2025-09-01', valor_bruto: '100', valor_pago_na_data: '20', multa_percentual: '2' }] });
  assert.match(html, /id="multa-1"[^>]*type="number"[^>]*min="0"[^>]*max="100"[^>]*step="0.0001"[^>]*value="2"/);
  assert.match(html, /id="saldo-1"[^>]*value="R\$ 80,00"/);
  assert.match(html, /Recebe a mesma atualização e os mesmos juros da parcela/);
  assert.match(render(Processamento), /id="multa-1"[^>]*value="0"/);
});

test('resultado discrimina multa nominal, atualização e juros próprios', () => {
  const html = render(ResultadoPrincipal, {
    ...resultado,
    resumo: { ...resultado.resumo, totais_componentes: { selic: '12', multa_parcela: '2.24' } },
    parcelas: [{ ...resultado.parcelas[0], componentes: { ...resultado.parcelas[0].componentes, multa_parcela: { data_inicial: '2025-09-01', data_final: '2026-08-31', base_calculo: '100', fator_acumulado: null, taxa_acumulada_percentual: '2', valor: '2.24' } }, multa_detalhes: { valor_original: '2', correcao_monetaria: '0.24', juros_mora: '0' } }],
  });
  for (const texto of ['Multa e encargos', 'Nominal:', 'Atualização:', 'Juros:']) assert.match(html, new RegExp(texto));
});

test('termo inicial individual dos juros permanece disponível quando selecionado', () => {
  const html = render(Processamento, null, { dadosGerais: { criterio_inicio_juros: 'por_parcela' } });
  assert.match(html, /class="parcel-interest"/);
  assert.match(html, /id="juros-1"/);
  assert.match(html, /Em branco: vencimento da parcela/);
  assert.doesNotMatch(render(Processamento), /id="juros-1"/);
});

test('ambas as categorias compartilham espaçamento ampliado entre blocos', async () => {
  const css = await readFile(new URL('../src/index.css', import.meta.url), 'utf8');
  assert.match(css, /--calculation-block-gap:\s*64px/);
  for (const categoria of ['processamento', 'honorarios']) {
    assert.ok(css.includes(`.${categoria}-page form>fieldset>.sheet-panel { margin-bottom: var(--calculation-block-gap); }`));
    assert.ok(css.includes(`.${categoria}-page .page-intro { margin-bottom: var(--calculation-block-gap); }`));
  }
  assert.match(css, /\.honorarios-page form>fieldset>\.debt-grid \{ margin-bottom: var\(--calculation-block-gap\); \}/);
  assert.match(css, /\.principal-result \{ margin-top: var\(--calculation-block-gap\);/);
  assert.match(css, /\.honorarios-page \.honorarios-result \{ margin-top: var\(--calculation-block-gap\);/);
});

test('critérios e explicações ficam no bloco Dados do cálculo, antes das parcelas, em todos os padrões', () => {
  for (const [perfil, textos] of [
    ['selic_ipcae_poupanca_v1', ['Tema 905', 'à poupança', 'Meses parciais']],
    ['selic_ipcae_2aa_v1', ['limitado à SELIC', 'aos juros de 2% ao ano', 'Meses parciais']],
    ['selic_cjf_v1', ['SELIC simples por competência:', 'A taxa do mês é aplicada no mês seguinte', 'Meses futuros']],
  ]) {
    const html = render(Processamento, null, { perfil });
    const dados = html.match(/<section\b[^>]*aria-labelledby="dados-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
    const detalhes = dados.match(/<details class="quiet-details criteria-note">([\s\S]*?)<\/details>/)[1];
    assert.match(detalhes, /Ver os critérios aplicados/);
    assert.match(detalhes, /id="indices-disponiveis">Consultando os índices…/);
    assert.doesNotMatch(dados.slice(0, dados.indexOf('<details')), /Consultando os índices|Índices completos/);
    for (const texto of textos) assert.ok(detalhes.includes(texto), `Critérios de ${perfil}: ${texto}`);
    assert.equal((html.match(/Ver os critérios aplicados/g) || []).length, 1);
    assert.ok(html.indexOf('Ver os critérios aplicados') < html.indexOf('id="parcelas-titulo"'));
    assert.doesNotMatch(html.slice(html.indexOf('</fieldset>')), /Ver os critérios aplicados/);
  }
});

test('início dos juros e sua data compartilham a grade superior dos dados do cálculo', () => {
  for (const perfil of ['selic_ipcae_poupanca_v1', 'selic_ipcae_2aa_v1', 'selic_cjf_v1']) {
    for (const criterio of ['vencimento', 'citacao', 'data_fixa', 'por_parcela']) {
      const html = render(Processamento, null, { perfil, dadosGerais: { criterio_inicio_juros: criterio } });
      const grade = html.match(/<div class="field-grid processamento-base-grid[^"]*">([\s\S]*?)<details/)[1];
      const temJuros = perfil !== 'selic_cjf_v1';
      const temData = temJuros && ['citacao', 'data_fixa'].includes(criterio);
      assert.ok(grade.includes('id="data-base"'));
      assert.ok(grade.includes('id="padrao-calculo"'));
      assert.equal(grade.includes('id="inicio-juros"'), temJuros);
      assert.equal(grade.includes('id="data-inicio-juros"'), temData);
      assert.doesNotMatch(html, /processamento-juros-grid/);
      const campos = ['data-base', 'padrao-calculo', ...(temJuros ? ['inicio-juros'] : []), ...(temData ? ['data-inicio-juros'] : [])];
      const posicoes = campos.map(id => grade.indexOf(`id="${id}"`));
      assert.deepEqual(posicoes, [...posicoes].sort((a, b) => a - b));
      if (temData) assert.match(grade, /id="data-inicio-juros"[^>]*required=""/);
    }
  }
});

test('critérios usam fonte menor e períodos seguidos de dois-pontos na mesma linha', async () => {
  for (const [perfil, periodos] of [
    ['selic_ipcae_poupanca_v1', ['01/07/2009 a 08/12/2021', '09/12/2021 a 09/09/2025', 'A partir de 10/09/2025']],
    ['selic_ipcae_2aa_v1', ['01/07/2009 a 08/12/2021', '09/12/2021 a 09/09/2025', 'A partir de 10/09/2025']],
  ]) {
    const html = render(Processamento, null, { perfil });
    for (const periodo of periodos) assert.ok(html.includes(`<strong>${periodo}:</strong> `));
    assert.match(html, /IPCA-E/);
    assert.match(html, /Meses sem índices completos permanecem bloqueados/);
    assert.match(html, /Não altera os períodos do IPCA-E ou da SELIC/);
  }
  const css = await readFile(new URL('../src/index.css', import.meta.url), 'utf8');
  assert.match(css, /\.processamento-page \.criteria-note \{ font-size: 11px; line-height: 1\.55;/);
  assert.match(css, /\.processamento-page \.criteria-note \.criteria-list \{ gap: 6px;/);
  assert.match(css, /\.processamento-page \.criteria-note \.criteria-list strong \{ display: inline;/);
});

test('mover o aviso de índices não remove limites e erros do campo de data', async () => {
  const fonte = await readFile(new URL('../src/pages/Processamento.tsx', import.meta.url), 'utf8');
  const campoData = fonte.match(/<Input id="data-base"[^\n]+/)[0];
  assert.match(campoData, /min=\{criterios\?\.inicio\} max=\{limiteDataBase\}/);
  assert.match(campoData, /disabled=\{!cobertura\} required/);
  assert.match(campoData, /error=\{limiteDataBase/);
  assert.doesNotMatch(campoData, /hint=/);
  const aviso = fonte.match(/<p id="indices-disponiveis">[^\n]+/)[0];
  assert.match(aviso, /limiteDataBase \? `Índices completos até \$\{formatarData\(limiteDataBase\)\}\.`/);
  assert.match(aviso, /cjf && cobertura\?\.data_referencia_selic_maxima/);
  assert.match(aviso, /Última competência disponível/);
});

test('resumo antes de calcular destaca valores sem contorno e preserva as rubricas separadas', async () => {
  const html = render(Processamento, null, { custasDespesas: [{ numero: 1, nome: 'Taxa de teste', data: '2025-09-01', valor: '20' }] });
  const resumo = html.match(/<div class="calculation-actions">([\s\S]*?)<\/fieldset>/)[1];
  for (const texto of ['Principal após pagamentos', 'Custas e despesas informadas', '100,00', '20,00', 'Calcular atualização']) {
    assert.ok(resumo.includes(texto), `Resumo deve preservar ${texto}`);
  }
  const css = await readFile(new URL('../src/index.css', import.meta.url), 'utf8');
  assert.match(css, /\.processamento-page \.calculation-actions \{ border: 0;[^}]*background: var\(--paper\)/);
  assert.match(css, /\.processamento-page \.calculation-actions strong \{[^}]*color: var\(--navy\);[^}]*font-size: clamp\(22px, 2\.2vw, 26px\)/);
  assert.match(css, /\.processamento-page \.calculation-actions \.calculation-totals \{[^}]*grid-template-columns: repeat\(auto-fit/);
});

test('resultado fica depois do formulário, com PDF, encargos, custas e memória preservados', () => {
  const html = render(Processamento, resultado);
  assert.ok(html.indexOf('class="principal-result"') > html.indexOf('</form>'));
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  for (const texto of ['Resultado do cálculo', 'Baixar PDF', 'Valores por parcela', 'Taxa de teste', 'Critérios e fontes', 'Conferir a memória mensal', 'Planilhas e memória completa']) {
    assert.ok(html.includes(texto), `Deve preservar ${texto}`);
  }
  assert.match(html, /12,0000%/);
  assert.match(html, /133,00/);
});

test('rotas antigas redirecionam para a tela unificada e calcular não navega', async () => {
  const app = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
  const processamento = await readFile(new URL('../src/pages/Processamento.tsx', import.meta.url), 'utf8');
  for (const rota of ['conferencia', 'exportacao']) {
    assert.ok(app.includes(`path="/${rota}" element={<Navigate to="/processamento" replace />}`));
  }
  assert.doesNotMatch(processamento, /useNavigate|navigate\(/);
});

test('honorários, cumprimento e destaques ficam entre descontos e custas, inicialmente opcionais', () => {
  const html = render(Processamento);
  const ids = ['descontos-titulo', 'honorarios-principais-titulo', 'cumprimento-titulo', 'destaques-titulo', 'principal-custas-titulo'];
  const posicoes = ids.map(id => html.indexOf(`id="${id}"`));
  assert.ok(posicoes.every(p => p >= 0));
  assert.deepEqual(posicoes, [...posicoes].sort((a, b) => a - b));
  assert.doesNotMatch(html, /id="honorarios-percentual"|id="contratuais-percentual"/);
  assert.match(html, /Destacar honorários contratuais/);
});

test('as três bases exibem os campos próprios sem exigir dados de outra base', () => {
  for (const base of ['proveito_economico', 'valor_causa', 'valor_certo']) {
    const html = render(Processamento, null, { honorariosSucumbenciais: { aplicar: true, base, percentual: '20', valor_causa: '1000', data_protocolo: '2025-09-15', indice: 'ipcae', valor_certo: '100' } });
    for (const rotulo of ['Valor do proveito econômico', 'Valor da causa atualizado', 'Valor certo']) assert.ok(html.includes(rotulo));
    assert.equal(html.includes('id="honorarios-percentual"'), base !== 'valor_certo');
    assert.equal(html.includes('id="honorarios-protocolo"'), base === 'valor_causa');
    assert.equal(html.includes('id="honorarios-valor-certo"'), base === 'valor_certo');
    if (base === 'valor_causa') {
  assert.match(html, /IPCA-E · IBGE \/ SGS 7478/);
      assert.match(html, /IPCA · IBGE \/ Banco Central/);
      assert.match(html, /sem juros/);
    }
  }
});

test('honorários não incluídos usam o mesmo aviso e ação sem bordas das custas', () => {
  const html = render(Processamento);
  const bloco = html.match(/<section[^>]*aria-labelledby="honorarios-principais-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
  assert.match(bloco, /<div class="costs-empty">[\s\S]*Honorários sucumbenciais não incluídos\./);
  assert.match(bloco, /<button[^>]*class="[^"]*cost-add[^>]*type="button"[^>]*aria-expanded="false"/);
  assert.match(bloco, /Adicionar honorários sucumbenciais/);
  assert.doesNotMatch(bloco, /type="checkbox"|Incluir honorários sucumbenciais|honorarios-principais-campos/);
  assert.ok(bloco.indexOf('costs-empty') < bloco.indexOf('Adicionar honorários sucumbenciais'));
});

test('honorários incluídos exibem campos e ação de remover, sem repetir o aviso vazio', () => {
  const html = render(Processamento, null, { honorariosSucumbenciais: { aplicar: true, base: 'valor_causa', percentual: '20', valor_causa: '1000', data_protocolo: '2025-09-15', indice: 'ipca', valor_certo: null } });
  const bloco = html.match(/<section[^>]*aria-labelledby="honorarios-principais-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
  assert.match(bloco, /id="honorarios-principais-campos"/);
  assert.match(bloco, /Remover honorários sucumbenciais/);
  assert.match(bloco, /aria-expanded="true" aria-controls="honorarios-principais-campos"/);
  assert.doesNotMatch(bloco, /costs-empty|Adicionar honorários sucumbenciais|type="checkbox"/);
});

test('adicionar e remover honorários só altera inclusão e preserva todos os dados', () => {
  const original = { aplicar: false, base: 'valor_causa', percentual: '20', valor_causa: '1000', data_protocolo: '2025-09-15', indice: 'ipca', valor_certo: '100' };
  let config = { ...original };
  function encontrarAcao(elemento) {
    if (!elemento || typeof elemento !== 'object') return null;
    if (elemento.props?.className === 'cost-add') return elemento;
    return [elemento.props?.children].flat(Infinity).map(encontrarAcao).find(Boolean) || null;
  }
  for (const aplicar of [true, false, true]) {
    const arvore = HonorariosPrincipaisForm({ config, dataBase: '2026-08-31', onChange: proximo => { config = proximo; } });
    const acao = encontrarAcao(arvore);
    assert.ok(acao);
    assert.equal(acao.props.type, 'button');
    assert.equal(acao.props.variant, 'ghost');
    assert.equal(acao.props['aria-expanded'], config.aplicar);
    acao.props.onClick();
    assert.deepEqual(config, { ...original, aplicar });
    assert.deepEqual(original, { aplicar: false, base: 'valor_causa', percentual: '20', valor_causa: '1000', data_protocolo: '2025-09-15', indice: 'ipca', valor_certo: '100' });
  }
});

test('cumprimento permite escolhas independentes e destaque percentual sem custas', () => {
  const html = render(Processamento, null, { cumprimentoSentenca: { aplicar_multa: true, aplicar_honorarios: false, incluir_sucumbenciais_base: true, destacar_contratuais: true, percentual_contratuais: '30', base_contratuais: 'credito_parte' } });
  assert.match(html, /Multa de 10%/);
  assert.match(html, /Honorários advocatícios de 10%/);
  assert.match(html, /id="contratuais-percentual"[^>]*required=""[^>]*value="30"/);
  assert.match(html, /não acresce ao cálculo e nunca incide sobre custas/);
  assert.match(html, /não incidem sobre a multa do art. 523/);
  assert.match(html, /sem honorários da sentença, custas ou despesas/);
  assert.doesNotMatch(html, /Incluir os honorários sucumbenciais da sentença na base/);
});

test('destaques são um bloco próprio sem controles contratuais dentro do cumprimento', () => {
  const html = render(Processamento);
  const cumprimento = html.match(/<section[^>]*aria-labelledby="cumprimento-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
  const destaques = html.match(/<section class="sheet-panel" aria-labelledby="destaques-titulo">([\s\S]*?)<\/section>/)[1];
  assert.match(cumprimento, /Multa de 10%/);
  assert.match(cumprimento, /Honorários advocatícios de 10%/);
  assert.doesNotMatch(cumprimento, /Destacar honorários contratuais|contratuais-percentual|Divisão do crédito|Acréscimos e destaque/);
  assert.match(destaques, /<h2 id="destaques-titulo">Destaques<\/h2>/);
  assert.match(destaques, /Divisão do crédito/);
  assert.match(destaques, /Destacar honorários contratuais/);
  assert.match(destaques, /não acresce ao cálculo e nunca incide sobre custas ou despesas/);
  assert.doesNotMatch(destaques, /contratuais-percentual|contratuais-base|Multa de 10%|Honorários advocatícios de 10%/);
});

test('campos dos destaques independem dos acréscimos e preservam as duas bases existentes', () => {
  for (const [aplicar_multa, aplicar_honorarios] of [[false, false], [true, false], [false, true], [true, true]]) {
    for (const base_contratuais of ['credito_parte', 'total_sem_custas']) {
      const html = render(Processamento, null, { cumprimentoSentenca: { aplicar_multa, aplicar_honorarios, destacar_contratuais: true, percentual_contratuais: '30', base_contratuais } });
      const destaques = html.match(/<section[^>]*aria-labelledby="destaques-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
      const cumprimento = html.match(/<section[^>]*aria-labelledby="cumprimento-titulo"[^>]*>([\s\S]*?)<\/section>/)[1];
      assert.match(destaques, /id="contratuais-percentual"[^>]*required=""[^>]*value="30"/);
      assert.ok(destaques.includes(`value="${base_contratuais}" selected=""`));
      assert.match(destaques, /não acresce ao cálculo e nunca incide sobre custas ou despesas/);
      assert.doesNotMatch(cumprimento, /contratuais-percentual|contratuais-base|Destacar honorários contratuais/);
      assert.equal(destaques.includes('exclui os honorários sucumbenciais e do art. 523'), base_contratuais === 'credito_parte');
    }
  }
});

test('alternar destaques preserva percentual, base e opções do cumprimento sem mutar a entrada', () => {
  const original = { aplicar_multa: true, aplicar_honorarios: true, destacar_contratuais: false, percentual_contratuais: '30', base_contratuais: 'total_sem_custas' };
  let config = { ...original };
  function encontrarToggle(elemento) {
    if (!elemento || typeof elemento !== 'object') return null;
    if (elemento.type === 'input' && elemento.props?.type === 'checkbox') return elemento;
    return [elemento.props?.children].flat(Infinity).map(encontrarToggle).find(Boolean) || null;
  }
  for (const destacar_contratuais of [true, false, true]) {
    const toggle = encontrarToggle(DestaquesForm({ config, onChange: proximo => { config = proximo; } }));
    assert.ok(toggle);
    toggle.props.onChange({ target: { checked: destacar_contratuais } });
    assert.deepEqual(config, { ...original, destacar_contratuais });
  }
  assert.equal(original.destacar_contratuais, false);
});

test('resultado distingue honorários judiciais e destaque contratual do total', () => {
  const html = render(ResultadoPrincipal, { ...resultado,
    honorarios_sucumbenciais: { base: 'proveito_economico', descricao_base: 'Proveito econômico', percentual: '20', base_atualizada: '112', valor: '22.40', memoria: [] },
    cumprimento_sentenca: { credito_parte: '112', sucumbenciais_na_base: '0', base_calculo: '112', aplicar_multa: true, aplicar_honorarios: true, multa: '11.20', honorarios: '11.20' },
    destaque_contratuais: { descricao_base: 'Crédito da parte', base_calculo: '123.20', percentual: '30', valor: '36.96', saldo_apos_destaque: '86.24' },
  });
  for (const texto of ['Honorários sucumbenciais', 'Cumprimento de sentença', 'Honorários contratuais destacados', 'não altera o total devido']) assert.ok(html.includes(texto));
  const resumo = html.match(/<div class="result-metrics">([\s\S]*?)<p class="result-explanation"/)[1];
  assert.doesNotMatch(resumo, /36,96|Honorários contratuais/);
  assert.match(html, /Base comum:[\s\S]*?112,00 · parcelas atualizadas após descontos, sem honorários da sentença, custas ou despesas/);
  assert.doesNotMatch(html, /\+ honorários da sentença/);
});
