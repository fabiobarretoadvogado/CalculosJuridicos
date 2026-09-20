# Depósito judicial: poupança em operação independente

Registro de 18/09/2026. Extensão reutilizável da tela Principal e honorários, limitada à operação Descontos. Perfil interno `poupanca_deposito_v1`; não altera os perfis da dívida nem acrescenta remuneração bancária à categoria autônoma de honorários.

## Regra e fontes

- Série oficial BCB SGS 195, remuneração total da poupança para depósitos novos desde 04/05/2012. Cada taxa diária identifica um período mensal de aniversário por `data` e `dataFim`; não se usa média mensal nem o dia 1 indiscriminadamente.
- Fatores reinvestidos apenas em aniversários completos; dias 29, 30 e 31 normalizados para o dia 1 do mês seguinte. Sem pró-rata de período incompleto, IPCA ou SELIC adicionais, ou juros moratórios separados.
- Parte expressamente fora da conta excluída da base remunerada e devolvida nominalmente ao abatimento. Lançamentos desmarcados preservados, mas não calculados. Índice ausente gera erro; ausência não equivale a taxa zero.
- Cobertura limitada pela data de consulta e pelos períodos oficiais disponíveis; publicação de uma taxa com vencimento futuro não antecipa o rendimento. Snapshot consultado em 18/09/2026, até o registro de 17/09/2026, combinado com os snapshots históricos existentes. Cálculo local sem consulta obrigatória à internet.
- A remuneração bancária é uma estimativa, não um fato de liberação ou quitação. O programa não decide a incidência do Tema 677 ou a natureza jurídica do depósito. Dedução definitiva deve usar o saldo real da conta na entrega ao credor; resgate do mesmo depósito não pode ser abatido novamente.

Fontes primárias:

- [BCB — SGS 195, consulta baixada](https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados?formato=json&dataInicial=09/12/2021&dataFinal=18/09/2026).
- [BCB — depósitos nos dias 29, 30 e 31](https://www.bcb.gov.br/meubc/faqs/p/posso-abrir-caderneta-de-poupanca-nos-dias-29-30-e-31-qual-a-diferenca).
- [BCB — remuneração da poupança](https://www.bcb.gov.br/meubc/faqs/p/como-sao-remunerados-os-depositos-da-poupanca).
- [STJ — Informativo 755, revisão do Tema 677](https://scon.stj.jus.br/jurisprudencia/externo/informativo/?acao=pesquisarumaedicao&from=feed&livre=0755.cod.). A tese distingue depósito em garantia/penhora e efetiva entrega; não foi imposta automaticamente pelo perfil.

## Caso 0072089-11.2024.8.25.0001 / 202411802540

Fonte preservada: `C:/Users/fabio/Downloads/202411802540.pdf`. Comprovante bancário na p. 61: depósito em 30/12/2025 de R$ 5.313,93. Retenção nominal de IR na p. 88: R$ 531,89. Manifestação na p. 90: composição bruta de R$ 5.845,82, referência 31/12/2025. A data informada pelo usuário foi mantida; tanto 30 quanto 31/12 conduzem ao primeiro aniversário em 01/01/2026. O usuário informou que o depósito ainda não foi liberado e confirmou expressamente poupança apenas sobre a conta, com IR nominal.

Original R$ 5.800,00, fixação em 14/11/2024; dívida pela SELIC simples, conforme perfil anteriormente escolhido. Não reutilizada a conta judicial de maio nem o abatimento antigo atualizado pela SELIC. O cálculo parte do crédito original.

Referência de 01/09/2026, última competência SELIC aplicada: agosto/2026.

| Rubrica | Valor |
| --- | --- |
| Original | R$ 5.800,00 |
| SELIC simples acumulada | 24,15% / R$ 1.400,70 |
| Dívida atualizada | R$ 7.200,70 |
| Principal efetivamente destinado à conta | R$ 5.313,93 |
| Poupança estimada: oito aniversários completos | R$ 289,50 |
| Saldo bancário estimado | R$ 5.603,43 |
| IR retido, abatimento nominal | R$ 531,89 |
| Total do abatimento na referência | R$ 6.135,32 |
| Diferença adicional estimada | R$ 1.065,38 |

Fator independente: `1.054478811982017861161438793`, produto das oito taxas oficiais com início no dia 1 de janeiro a agosto/2026. Arredondamento financeiro HALF_UP ao centavo, com precisão integral durante a acumulação. Saldo da conta pode divergir por lançamentos, remuneração contratual efetiva ou arredondamentos bancários; conferir extrato.

R$ 1.065,38 é diferença **adicional ao depósito ainda pendente de entrega**, não o valor total a receber nem quitação reconhecida. IR nominal tratado conforme confirmação do usuário. Aplicabilidade jurídica e saldo bancário definitivo permanecem sujeitos a conferência.

Entrada nova: `backend/examples/processo_0072089-11.2024.8.25.0001_deposito_poupanca.json`. Relatório novo: `output/pdf/calculo_0072089-11.2024.8.25.0001_deposito_poupanca.pdf`, acompanhado de JSON, Excel e CSV auditáveis. Entradas e relatórios anteriores preservados.

## Validação e limites

- Motor e API concordam integralmente no caso; conferência independente do produto dos fatores, remuneração e IR nominal.
- 55 testes focados passaram: depósitos, descontos e PDF; incluem aniversários intermediários, dias 29/30/31, ausência de índice, período incompleto, lançamento desmarcado, remuneração separada do IR e diferença de setembro maior que a de maio.
- 48 testes do frontend passaram; checagem de tipos, lint e build concluídos. Perfil bancário aparece apenas nos descontos, sem campos de juros moratórios adicionais. Estilos e pontos de quebra existentes preservados.
- PDF final: duas páginas A4 paisagem, inspeção visual de ambas, tabelas alinhadas, único cabeçalho por tabela, cabeçalho junto à primeira linha e total em destaque. Mantida identidade institucional. Corrigida a proteção de quebra do primeiro cabeçalho das tabelas principal e de descontos.
- Na execução geral anterior, 399 testes passaram e quatro falharam em outras rotinas: `test_deflacao_parcelas_adicionais_sem_nova_correcao_e_pdf`, `test_selic_ate_ec136_nao_aplica_tema905_ou_poupanca_antes_da_transicao`, `test_inicio_juros_nao_limita_selic_nem_ipcae` e `test_mes_corrente_parcial_nao_e_completo`. Não alterados os critérios dessas rotinas neste escopo; não se declara aprovação da suíte geral.
- A inspeção interativa do navegador ficou pendente por indisponibilidade da automação local de interface; acesso HTTP ao build e testes do formulário não substituem essa inspeção. Não alteradas permissões de segurança como contorno.
- Backend reiniciado com a versão final e verificado por requisições reais: perfil publicado, diferença de R$ 1.065,38, abatimento de R$ 6.135,32 e PDF de duas páginas com o primeiro cabeçalho e a primeira linha na mesma página. Build servido em `http://127.0.0.1:4173/processamento`, HTTP 200, arquivo `index-BMHWbQI4.js` contendo o novo perfil. Exibição do PDF solicitada no painel do aplicativo; resposta de abertura enfileirada, não confirmação visual de abertura.

Pendências para cálculo definitivo: extrato atualizado da conta judicial e data da efetiva liberação. Não presumidos movimentos bancários, remunerações futuras ou pagamento recebido.
