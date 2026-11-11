# Bases oficiais canônicas — migração local de 06/10/2026

## Resultado entregue

Por escolha expressa do usuário, o código passa a usar somente as novas bases oficiais e pacotes schema 2. Os cinco arquivos `backend/data/indices/{igpm,inpc,ipca,selic,taxa_legal}.csv` e a pasta vazia `indices` foram removidos da distribuição. Nenhum pacote de aplicativo foi gerado, instalado ou publicado; a última edição instalada/publicada continua 1.16, técnica 2026.9.20.16.

O leitor/publicador aceita exclusivamente schema 2 no canal `indices-v2-<revisão>`. Foram retirados o conversor de pacotes antigos, listas por formato, cópias derivadas, metadados de pacote de origem, calendário `metodologia_1am.json` e seus testes. A lista canônica em `index_data/store.py` contém 18 arquivos. A busca de atualização ignora o canal antigo, inclusive quando sua revisão é mais recente.

## Fontes e cobertura

| Série | Fonte canônica utilizada | Registros anteriores conferidos | Cobertura canônica atual |
| --- | --- | --- | --- |
| IPCA | `ipca_oficial.json`, IBGE / SGS 433 | 80 | 206 competências, 2009-07 a 2026-08 |
| INPC | `inpc_oficial.json`, IBGE / SGS 188 | 80 | 206 competências, 2009-07 a 2026-08 |
| IGP-M | `igpm_oficial.json`, FGV / SGS 189 | 81 | 81 competências, 2020-01 a 2026-09 |
| SELIC | União conciliada dos JSONs oficiais históricos, simplificados e EC 136, SGS 4390 | 81 | 482 competências, 1986-08 a 2026-09 |

Todos os percentuais e fatores sobrepostos dos quatro CSVs conferiram com os leitores canônicos; as deflações foram preservadas. INPC e IGP-M foram consultados diretamente na API do Banco Central em 06/10/2026. URLs, série, data de consulta e conferência ficam nos JSONs. A referência oficial do INPC é https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=188 e a do IGP-M é https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=189.

O INPC anterior só cobria 2020 em diante; Civil 3 agora lê o histórico oficial desde 2009-07. Períodos que antes não tinham cobertura podem gerar novos resultados ao recalcular, embora as taxas sobrepostas permaneçam idênticas. O limite Civil 3 continua 01/09/2026, após a última competência INPC publicada. Custas continuam em IPCA-E, e os limites independentes Civil 1 foram preservados. Os motores próprios da SELIC conservam os bloqueios de competência parcial e a referência mensal existente.

O atualizador `scripts/atualizar_indices_mensais.py` consulta somente INPC/IGP-M, conserva deflações e valida continuidade e cobertura antes da gravação atômica. `--verificar` não grava. Ele não gera CSVs nem publica.

## Pacote antigo ativo e dados preservados

A conferência final foi feita sobre a base ativa real, somente por leitura. O pacote anterior `20261001T192301829327Z`, identidade `b335dfa828e4198e964a857a956cd3add7bab41385aaa8e8083335c9b80fbb69`, é rejeitado depois da verificação da assinatura por ter formato antigo. A base oficial incorporada fica em uso com a mensagem:

> O pacote local utiliza um formato antigo e foi ignorado. Somente as novas bases oficiais incorporadas estão em uso. Os arquivos anteriores e os cálculos salvos foram preservados.

O conteúdo de `active.json` e todos os 21 arquivos do pacote anterior permaneceram idênticos. Eventual material derivado gerado nas conferências anteriores permanece ignorado e intocado no perfil real; o código final não cria, lê ou mantém esse mecanismo. Pacotes, cálculos salvos, chaves, bancos e PDFs reais não foram apagados ou reescritos. A importação de bancos de cálculos salvos permanece intacta por ser escopo distinto.

Cópias dos cinco CSVs retirados ficam em `build/migracao_bases_20261006/originais` como recuperação local, fora de `backend/data` e da lista de publicação; elas não alimentam motores nem pacotes. A evidência final está em `build/migracao_bases_20261006/verificacao_pacote_real.json`.

Hash SHA-256 da base canônica atual: `0436070748e7e688130485454829e803776919ef0693ae6597892bdf4968c16a`.

## Regra financeira antiga preservada

**Revisão posterior, 22/10/2026:** por decisão expressa do usuário, o motor configurável antigo, seus módulos exclusivos de validação e abatimento, os dois identificadores antigos `taxa_legal` e o CSV local foram removidos. Os parágrafos seguintes descrevem o estado histórico desta migração de 06/10/2026, não o estado atual. Os perfis Civil 2 e Civil 3 preservam seus juros simples de 1% ao mês; a série oficial permanece independente.

`TipoJuros.TAXA_LEGAL` no motor configurável antigo já apurava 1% ao mês simples pelo fallback. Esse regime permanece explícito no código e identificado na memória e nos alertas. Não há série antiga ou calendário externo para essa regra, e ela não é substituída pela Taxa Legal oficial SGS 29543. O perfil Civil 1 continua usando a SGS 29543 em seu leitor próprio, com cobertura desde 30/08/2024.

A correção pelo enum antigo `IndiceCorrecao.TAXA_LEGAL` tinha um problema preexistente: a normalização remove o sublinhado e buscava `taxalegal.csv`, que não existia. Os valores efetivos, ausência de correção e alertas de competências ausentes foram preservados, acrescentando aviso claro de que a modalidade exige revisão expressa. Isso não certifica a correção financeira dessa modalidade. Nenhum encargo novo foi ativado automaticamente. A API antiga também não tinha `ipcae.csv`; os perfis oficiais de IPCA-E continuam em seus leitores existentes.

## Validação da versão final simplificada

Foram executados somente os testes afetados: `test_index_data.py`, `test_fontes_oficiais.py`, `test_civil_3.py`, `test_correcao.py`, `test_juros.py` e `test_limites_civil_1.py`. Resultado final: **33 testes passaram em 13,69 segundos**. Não foi executada suíte completa ou inspeção visual.

A rodada cobre bases conciliadas, lista assinada de 18 arquivos, pacote schema 2 preparado com chave efêmera e extraído/validado, ativação atômica, assinatura e arquivo adulterados, redução de cobertura, estabilidade da base durante uma operação, catálogo, falha de rede, rejeição do pacote antigo sem escrita, busca exclusiva do canal v2, deflação, cobertura histórica INPC, regra de juros de 1% e limitação da correção antiga, além das datas independentes Civil 1.

Durante a implementação inicialmente descartada, um teste de adulteração atingiu temporariamente a fonte INPC incorporada ao cair em um fallback. O arquivo foi restaurado integralmente de uma cópia anterior ao teste e comparado com todas as 206 competências e os metadados da resposta oficial. Hash restaurado e reconfirmado na versão final: `0d3d2b02c4bdcb965e578804b7535c3dc755fe426bb9fbc0480aab69551c0fe9`. Os testes próprios de conversão/adulteração derivada foram removidos; os testes finais não adulteram fontes do projeto. Nenhum banco ou dado de cálculo do usuário foi atingido.

Uma rodada inicial adicional de SELIC/CJF encontrou três expectativas preexistentes desatualizadas em `test_selic_cjf.py`: limite de setembro em vez de outubro, rejeição de 30/09/2026 apesar da competência de setembro encerrada e texto antigo no PDF. Esses testes e o motor SELIC/PDF não foram alterados para ampliar o escopo. A suíte completa não está declarada aprovada.

## Limites e próximos passos

A execução local está concluída. Para levar o código ao aplicativo instalado, será necessária autorização futura para gerar/publicar/instalar uma nova edição; só depois devem ser disponibilizados pacotes v2. Versões antigas ignoram o canal v2 e continuam com suas bases anteriores. A automação quinzenal armazenada não foi modificada nesta tarefa; seu procedimento deve seguir os JSONs oficiais e o canal v2 após a transição do aplicativo. A modalidade antiga de correção pelo nome taxa_legal continua exigindo revisão expressa, e as três expectativas antigas de SELIC/CJF ficam registradas como pendência de manutenção de testes.
