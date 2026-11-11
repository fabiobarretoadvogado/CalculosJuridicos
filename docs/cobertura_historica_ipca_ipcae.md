# Cobertura histórica de IPCA e IPCA-E

Ampliação local de 28/10/2026. IPCA SGS 433 desde **01/01/1980** e IPCA-E mensal SGS 10764 desde **01/01/1992**, ambos até setembro/2026 nesta consulta.

## Fontes e conciliação

- IPCA: resposta integral em `backend/data/fontes/bcb_ipca_1980_2026.json`, 561 competências; metadados, URL e SHA-256 em `ipca_oficial.json`.
- IPCA-E: resposta integral em `backend/data/fontes/bcb_ipcae_1992_2026.json`, 417 competências; metadados em `ipcae_historico_fonte.json`.
- A SGS 10764 foi comparada, competência a competência, ao IPCA-15 SGS 7478 já incorporado desde julho/2009. Todos os valores comuns coincidem. O snapshot usa o histórico anterior a julho/2009 e conserva os valores atuais do IPCA-15.
- Arquivos brutos, consultas e hashes acompanham a base de índices. A validação exige meses contínuos, conciliação numérica das séries e correspondência dos hashes. Uma divergência impede a ampliação; não é resolvida escolhendo silenciosamente uma taxa.
- A data de consulta das séries não consultadas permanece preservada. O IPCA foi consultado integralmente em 28/10/2026; o histórico do IPCA-E tem consulta própria, sem renovar a consulta da poupança, SELIC ou Taxa Legal.

Fontes: [SGS 433](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=433), [SGS 10764](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=10764), [IBGE IPCA-E](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9262-indice-nacional-de-precos-ao-consumidor-amplo-especial.html).

## Moeda da entrada e do resultado

O valor original é informado **na moeda vigente na data de origem**, identificada no formulário. Valores já convertidos em reais não devem ser lançados como se fossem valores nominais de uma data antiga. Entradas, pagamentos no vencimento, multas nominais, custas, descontos e honorários mantêm seus dados originais para reedição.

| Origem | Moeda | Divisor nominal acumulado para reais |
|---|---|---:|
| Até 27/02/1986 | Cruzeiro (Cr$) | 2.750.000.000.000 |
| 28/02/1986 a 15/01/1989 | Cruzado (Cz$) | 2.750.000.000 |
| 16/01/1989 a 15/03/1990 | Cruzado novo (NCz$) | 2.750.000 |
| 16/03/1990 a 31/07/1993 | Cruzeiro (Cr$) | 2.750.000 |
| 01/08/1993 a 30/06/1994 | Cruzeiro real (CR$) | 2.750 |
| Desde 01/07/1994 | Real (R$) | 1 |

Paridades e datas: [Histórico oficial das alterações da moeda nacional](https://www.gov.br/previdencia/pt-br/assuntos/previdencia-social/arquivos/aeps-2023/secao-xv-indicadores-economicos/apresentacao), cuja fonte é o Banco Central.

A equivalência nominal é calculada com `Decimal`, sem arredondamento intermediário, e multiplicada pelos fatores de inflação do período. Os cortes de moeda **não são taxas de inflação nem juros**. Os fatores de inflação continuam representando exclusivamente o produto das taxas mensais. A memória identifica a moeda de origem, cada transição, o divisor acumulado, o valor informado e seu equivalente nominal exato em reais.

Os demonstrativos e os totais financeiros são expressos em reais. A correção histórica exige data-base desde **01/07/1994**; os perfis principais conservam também seus limites próprios de data-base. Bases nominais usadas no cálculo mantêm precisão integral, mesmo abaixo de um centavo; a apresentação dos totais e componentes concilia os centavos. A multa nominal continua sendo arredondada na moeda de origem antes de sua atualização autônoma. Nenhuma conversão contratual especial, URV informada ou critério de expurgo é presumido.

## Correção e juros

- Civil 1, 2, 4 e 5: início da correção IPCA desde janeiro/1980. A Taxa Legal oficial continua desde 30/08/2024; Civil 2 conserva juros desde 01/07/2009; Civil 4 conserva a cobertura e as transições dos seus juros; Civil 5 conserva o início da sua série reconstruída e a transição para a taxa oficial.
- Fazenda Pública 1 a 4: correção pelo IPCA-E desde janeiro/1992. Antes de 01/07/2009 há somente correção. O usuário deve informar um termo de juros válido a partir de 01/07/2009; o sistema rejeita juros anteriores em vez de truncá-los. As transições de SELIC, poupança e 2% ao ano permanecem preservadas.
- Valor da causa, honorários fixados e custas usam a cobertura do índice selecionado. Custas continuam sem juros. A ampliação da fixação não antecipa a Taxa Legal nem os limites anteriores dos juros simples.
- INPC, SELIC/CJF, remuneração de depósitos e o perfil legado de IPCA-E anual mantêm suas coberturas e regimes.

## Manutenção

`scripts/ampliar_indices_historicos.py` consulta as duas séries, concilia todos os valores existentes e arquiva as respostas. `backend/data/fontes/gerar_snapshot.py` incorpora o histórico ao snapshot, preservando as outras séries. O pacote inclui as três novas fontes na lista fechada de arquivos; pacotes anteriores sem esses arquivos são recusados e a base incorporada é usada, preservando os arquivos antigos.

Esta alteração não publica índices, não cria instalador e não modifica a instalação existente.
