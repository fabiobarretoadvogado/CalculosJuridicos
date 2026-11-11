# Civil 5 — Taxa Legal com reconstituição histórica

O perfil `civil_5_taxa_legal_reconstruida_v1` mantém IPCA e juros simples da Taxa Legal em períodos independentes, com juros sobre o principal corrigido final. A extensão histórica pertence exclusivamente ao Civil 5. O Civil 1 continua utilizando a Taxa Legal oficial desde 30/08/2024.

## Cobertura e aplicação

| Encargo | Termo inicial disponível | Última referência desta entrega |
| --- | --- | --- |
| Correção IPCA, SGS 433 | 01/07/2009 | Agosto/2026; data-base máxima 01/09/2026 |
| Taxa Legal reconstruída | 01/06/2000 | Até 29/08/2024 |
| Taxa Legal publicada, SGS 29543 | 30/08/2024 | Outubro/2026; limite conjunto definido pelo IPCA |

Os juros podem anteceder a correção. São aceitos termos globais e individuais em parcelas, descontos e comparação de dívidas. O cálculo inclui o dia inicial e exclui a data-base. Meses parciais recebem a fração dias corridos / dias corridos do mês. O IPCA conserva deflações e fatores geométricos. As taxas de juros são somadas, com base constante igual ao principal corrigido final; não há consolidação de juros no corte temporal.

Em agosto/2024, a memória separa os dias até 29 e os dias desde 30 para identificar a origem da taxa. As duas partes usam a mesma taxa de agosto, 0,605306% ao mês, e continuam na mesma base de juros.

## Fontes e formação da taxa

A [Resolução CMN 5.171/2024](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=5171&tipo=resolu%C3%A7%C3%A3o+cmn) fornece a metodologia. A história anterior à publicação utiliza dados oficiais da [SELIC anual diária SGS 1178](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=1178) e do [IPCA-15 mensal SGS 7478](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=7478).

Para a competência m, os insumos são do mês anterior. Cada fator diário SELIC é `(1 + taxa anual / 100)^(1 / 252)`, arredondado a oito casas. Multiplicam-se os fatores dos dias úteis e arredonda-se o fator mensal a oito casas. O fator IPCA-15 é `1 + variação mensal / 100`, com quatro casas. A taxa percentual é `max(fator SELIC / fator IPCA-15 - 1, 0) × 100`, arredondada a seis casas conforme a NBR 5891, com metade para par. A formação utiliza precisão decimal de 48 casas. A taxa acumulada proporcional segue seis casas HALF_UP e os valores financeiros, HALF_UP ao centavo, mantendo o comportamento financeiro atual dos juros oficiais.

A série IPCA-15 consultada começa em maio/2000; o primeiro mês reconstruível é junho/2000. A consulta integral de 06/10/2026 contém 6.176 registros diários SELIC e 295 competências IPCA-15, de maio/2000 a novembro/2024. O snapshot oferece 291 taxas históricas de junho/2000 a agosto/2024. Cinco competências publicadas servem de conferência:

| Competência | Taxa reconstruída (%) | Taxa oficial (%) |
| --- | --- | --- |
| Agosto/2024 | 0,605306 | 0,605306 |
| Setembro/2024 | 0,676227 | 0,676227 |
| Outubro/2024 | 0,704241 | 0,704241 |
| Novembro/2024 | 0,385874 | 0,385874 |
| Dezembro/2024 | 0,171924 | 0,171924 |

Antes de 30/08/2024, o resultado identifica a taxa como reconstituída pela metodologia. Desde essa data, consulta exclusivamente a série publicada SGS 29543. Índice, fonte, memória de formação ou período ausentes impedem o cálculo; não há substituição por zero, SELIC integral ou juros de 1% ao mês.

## Arquivos canônicos e rastreabilidade

| Arquivo novo | SHA-256 |
| --- | --- |
| `backend/data/taxa_legal_reconstruida.json` | `12f3a68705fbe7e99fc538b055f2e9f009bb3ab1c4ca85984af04498682fabae` |
| `backend/data/fontes/bcb_selic_anual_civil5_2000_2009.json` | `568ddeecd49cd8843dc0bd75244fc5e9ddfa955bc804a53f42b4a3e2544ca60b` |
| `backend/data/fontes/bcb_selic_anual_civil5_2010_2019.json` | `7dd16f1592462e71ffaf571d9200eedcf020f425f2da8aaaa092ae9e042d92aa` |
| `backend/data/fontes/bcb_selic_anual_civil5_2020_2024.json` | `97dfbc86a9227e8c05517703b939c5d03ce50db70a24af026f2704fcae80e65b` |
| `backend/data/fontes/bcb_ipca15_civil5_2000_2024.json` | `daab3252814f1a8afc9100513d118e7fb529acaa6934aa5fa617a4cdf9645cb3` |

Os cinco arquivos integram a lista fechada FILES do pacote canônico formato 2. O publicador inclui seus tamanhos e hashes no manifesto assinado. A validação reconstrói a série a partir das fontes, concilia taxas e fatores, verifica as cinco coincidências publicadas e preserva cobertura e datas de consulta nas atualizações. A identidade da base já inclui os arquivos novos.

O motor registra origem por trecho, insumos do mês anterior, fatores, piso zero, taxas, frações, base e conciliação de centavos. JSON, Excel e CSV preservam a memória técnica, URLs e hashes. O PDF reutiliza os componentes e auxiliares comuns; quando houve período histórico, exibe uma única nota curta: “Taxa Legal reconstruída até 29/08/2024.” Os nomes dos perfis ficam na interface e nos dados.

O gerador reproduzível é `scripts/reconstruir_taxa_legal_civil5.py`. Ele grava somente a base e fontes exclusivas do Civil 5. Os snapshots oficiais anteriores e o motor Civil 1 foram preservados.

## Verificação dirigida

Em 06/10/2026, passaram 29 verificações selecionadas: 24 do Civil 5, duas dos limites do Civil 1 e três de integridade, catálogo e pacote. Foram cobertos reprodução das cinco taxas publicadas, fatores com oito casas, taxa com seis casas, piso zero, deflação, fontes ausentes, termos globais e individuais, juros anteriores à correção, corte 29/30, período sem incidência, três comparações financeiras exatas com Civil 1, multas, descontos, comparação de dívidas, API, recuperação e exportações PDF/Excel/CSV. Os PDFs foram conferidos por conteúdo textual, incluindo nota única e ausência do nome Civil 5; não foi feito exame visual.

A preparação local do pacote assinado passou em armazenamento temporário isolado. A primeira tentativa dos testes encontrou a pasta temporária padrão do Windows inacessível; a execução em uma pasta nova passou integralmente. O frontend passou na compilação TypeScript e no build. Conforme o escopo autorizado, não houve suíte completa, instalação, publicação, commit ou alteração de cálculo real.
