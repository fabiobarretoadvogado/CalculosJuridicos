# Honorários na tela principal e cumprimento de sentença

## Regras implementadas em 17/09/2026

Blocos inseridos após Descontos e antes de Custas e despesas processuais, com opções inicialmente desmarcadas. Reutilizados calcular_honorarios e calcular_multa_cpc523, sem mudar os perfis de atualização das parcelas ou a categoria autônoma de redução de dívida.

Honorários sucumbenciais: proveito econômico = total atualizado das parcelas, incluindo multa individual, menos descontos efetivamente abatidos, sem custas. Valor da causa = valor no protocolo corrigido exclusivamente por IPCA-E TJSP ou IPCA oficial SGS 433 desde a data do protocolo até a data-base, sem juros, seguido da aplicação do percentual informado. Valor certo = valor dos honorários informado já na data-base, sem nova atualização automática. O valor da causa nunca é somado ao principal.

Cumprimento: multa de 10% e honorários de 10% do art. 523 selecionados separadamente. Base exclusiva: parcelas atualizadas após descontos, sem honorários da sentença, custas ou despesas. Honorários da sentença nunca integram essa base em nenhuma das três modalidades, mas continuam compondo o total devido, uma única vez e em rubrica própria. Não aplicar 10% sobre a multa do próprio art. 523. O programa não verifica intimação ou decurso de prazo; exige revisão humana e alerta sobre Fazenda Pública.

Destaque contratual: percentual sobre o crédito da parte, por padrão, incluindo eventual multa do art. 523 e excluindo os honorários judiciais. Também é possível selecionar expressamente todo o total, excluindo custas e despesas. Em qualquer opção, não acresce ao total nem abate a dívida do executado. Exibir separadamente valor destacado e saldo dessa base após destaque.

Arredondamento HALF_UP ao centavo, sem alterar globalmente o contexto Decimal do motor antigo. Campos ocultos de bases não selecionadas não são enviados como operações ativas. Todas as edições invalidam o resultado anterior. Nenhum relatório de processo real foi sobrescrito.

## Fontes e cobertura

IPCA-E reutiliza a base oficial do TJSP já existente. IPCA arquivado em backend/data/ipca_oficial.json, consultado em 17/09/2026, série oficial SGS 433, com 206 competências de julho/2009 a agosto/2026. São índices distintos, nunca substituídos automaticamente. Falta de qualquer competência impede o cálculo; deflações são preservadas. As duas correções seguem o padrão diário proporcional do motor atual, incluindo os dias extremos. Entradas, fatores, fonte, memória própria e hash do snapshot IPCA permanecem auditáveis.

Fontes jurídicas conferidas:

- CPC/2015, arts. 523, 524 e 534: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm
- STJ, Informativo 636, REsp 1.757.033/DF: https://processo.stj.jus.br/jurisprudencia/externo/informativo/?livre=%40CNOT%3D016831
- IPCA SGS 433: https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=433

A exclusão de custas da base dos acréscimos é uma configuração deste projeto, expressamente exibida, não uma conclusão universal sobre quais despesas integram o débito de execução. Não presumir cabimento ou composição de uma execução real sem examinar seu título.

## Verificação inicial (antes da exclusão permanente dos honorários da base)

- 28 testes específicos das novas regras: quatro perfis, bases após multa e descontos, custas excluídas, três bases sucumbenciais, escolhas independentes do art. 523, inclusão opcional dos honorários da sentença, destaque sem acréscimo ou abatimento, índices oficiais, deflação, proporcionalidade, competência ausente, campos inválidos, defaults compatíveis, API, PDF, Excel e CSV.
- 154 testes selecionados de honorários principais, multa individual, cálculo simplificado, honorários por redução, descontos e PDF aprovados.
- 25 testes de interface aprovados; verificação de tipos, build e análise estática aprovados.
- PDFs demonstrativos em tmp/pdfs/honorarios_principais_20260917: uma parcela com custas e base da causa IPCA-E (seis páginas); vinte parcelas SELIC com proveito econômico (sete páginas); trinta e seis parcelas com múltiplos encargos e base da causa IPCA, observações e histórico excepcionalmente extensos (treze páginas). Gerador tmp/qa_honorarios_principais.py. As 26 páginas finais foram renderizadas e inspecionadas visualmente. Custas mantidas em página própria, valores contratuais separados, cabeçalhos únicos, continuidades alinhadas e linhas financeiras inteiras. Ajuste final impede cabeçalho da memória isolado. Com os novos blocos ativos, o resumo omite rubricas de períodos sem incidência; a tabela das parcelas continua explicitando os períodos não incidentes.
- Após o ajuste final de paginação, 51 testes de honorários principais, PDF e multas por parcela novamente aprovados.
- Build disponível na porta 4173 e API na porta 8000. Conferência real de POST /api/v1/calculo, POST /api/v1/calculo/exportar/pdf, GET /api/v1/honorarios/criterios-correcao e do HTML que carrega o build atual aprovada. Exemplo sintético: total R$ 1.473,84 idêntico com e sem destaque contratual; multa e honorários do art. 523 de R$ 97,92 cada, ambos sobre R$ 979,20; custas R$ 298,80 excluídas das bases; destaque 30% de R$ 913,92 = R$ 274,18. PDF retornado com quatro páginas. Conferidos também os dois índices na API: causa R$ 10.000,00 em 15/09/2025 até 31/08/2026 resulta em R$ 10.401,08 por IPCA-E e R$ 10.399,08 por IPCA, cada qual com doze trechos mensais sem juros e fonte própria. São dados de teste, não cálculo de processo real.

## Pendências e limites da validação

Bateria geral: 217 aprovados, quatro falhas fora dos novos blocos. Três cenários existentes da EC 136 divergem quanto à SELIC simulada ou cobertura; o relatório legado de correção mensal exclusiva pelo IPCA-E falha com KeyError ipcae_pre. Esse relatório legado não é o motor utilizado para corrigir o valor da causa no novo bloco. Não declarar a bateria geral integralmente aprovada.

Conferência visual da interface pelo navegador impedida nesta execução: o ambiente de automação termina ao inicializar com helper_unknown_error: apply deny-read ACLs, inclusive após uma recuperação. Não foram inseridos dados sintéticos nem recarregada a aba do usuário. A interface tem validação por renderização estática e build, mas a inspeção visual ampla e móvel permanece pendente.

## Exclusão permanente dos honorários da base do art. 523 - 17/09/2026

Regra expressamente solicitada pelo usuário: honorários sucumbenciais da sentença nunca entram na base dos acréscimos do cumprimento. Removido o seletor da tela; o motor usa somente o crédito líquido das parcelas. O campo antigo é mantido na API apenas como compatibilidade, desconsiderado e normalizado para false, inclusive quando recebido como true. A entrada normalizada fica registrada nas premissas, e sucumbenciais_na_base permanece zero no resultado por compatibilidade. O frontend não envia esse campo. Não foram alterados os perfis de atualização, os honorários da sentença em si, o destaque contratual ou relatórios existentes de processos reais.

Tela, PDF, Excel e CSV mostram a mesma base exclusiva. A cobertura de regressão inclui as quatro combinações dos acréscimos nos cinco perfis, entradas legadas com false/true, as três bases sucumbenciais e a conciliação das exportações. Relatórios sintéticos novos, sem sobrescrever os anteriores, são gerados em tmp/pdfs/honorarios_523_sem_sucumbenciais_20260917 para conferência visual.

Validação final desta alteração: 207 testes selecionados de honorários principais, IPCA + Taxa Legal, multas individuais, descontos, cálculo simplificado, PDF e honorários por redução aprovados; 30 testes de interface, análise estática, tipos e build aprovados. Não se trata de aprovação integral da bateria geral; as quatro falhas anteriores registradas acima não integram essa seleção.

Os três PDFs sintéticos possuem seis, sete e treze páginas (26 no total), todas renderizadas e inspecionadas visualmente. Preservados identidade, margens, tabelas, cabeçalhos únicos, continuação de colunas, rodapés, custas em página exclusiva e destaque contratual fora das rubricas acrescidas. O bloco do cumprimento explicita a exclusão dos honorários da sentença. Nenhum PDF de processo real foi sobrescrito.

API local reiniciada e conferida por POST real: parcelas R$ 10.000,00, descontos R$ 1.000,00 e honorários da sentença em valor certo de R$ 2.000,00 resultam em base do art. 523 de R$ 9.000,00 e multa/honorários de R$ 900,00 cada, mesmo com o campo legado enviado como true. A resposta registra sucumbenciais_na_base igual a zero e a entrada normalizada como false. Build index-Cl76LMUg.js servido na porta 4173 e conferido por HTTP, sem o seletor removido. Não foi recarregada a aba do usuário.

A tentativa de inspeção visual da interface nesta alteração também terminou na inicialização com helper_unknown_error: apply deny-read ACLs. A renderização estática, os testes e o build estão aprovados; a conferência visual no navegador amplo/móvel permanece pendente. A mesma limitação do leitor de imagens local foi contornada por leitura aprovada dos arquivos renderizados, permitindo a inspeção efetiva dos PDFs sem alterar configurações de segurança.
