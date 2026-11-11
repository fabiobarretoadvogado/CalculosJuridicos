# Conferência dos índices em 13/10/2026

Consulta direta às séries oficiais do BCB/SGS, com comparação integral das competências já arquivadas. Nenhum valor anterior divergiu. Dados novos foram adicionados sem estimativa nem preenchimento por zero.

| Base | Antes | Depois | Fonte |
| --- | --- | --- | --- |
| IPCA, SGS 433 | 08/2026 | 09/2026: 0,82% | https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=433 |
| INPC, SGS 188 | 08/2026 | 09/2026: 0,82% | https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=188 |
| Poupança de depósitos, SGS 195 | 28/09/2026 | 09/10/2026; nove registros novos de 01 a 09/10 | https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados?formato=json&dataInicial=09%2F12%2F2021&dataFinal=13%2F10%2F2026 |
| Meta SELIC auxiliar, SGS 432 | 06/09/2026 | 13/10/2026; 37 registros novos | https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01%2F09%2F2025&dataFinal=13%2F10%2F2026 |
| Salário mínimo federal | 2025: R$ 1.518,00 | 2026: R$ 1.621,00 | Decreto 12.797/2025: https://planalto.gov.br/ccivil_03/_ato2023-2026/2025/decreto/d12797.htm |

Também foram consultados IPCA-15/IPCA-E SGS 7478 (até 09/2026), SELIC mensal SGS 4390 (última competência fechada: 09/2026), Taxa Legal SGS 29543 (até 10/2026) e IGP-M SGS 189 (até 09/2026). Não houve competência nova nesses conjuntos. A taxa parcial da SELIC de 10/2026, visível na consulta de 13/10, não foi incorporada. As fontes históricas de SELIC até 11/2021 e da reconstrução do Civil 5 até 08/2024 conservam suas consultas próprias, pois os respectivos intervalos são fechados.

Os JSONs canônicos, as fontes diárias, o snapshot, a série EC 136 e os metadados próprios foram conciliados. Os arquivos de metadados registram URL, data da consulta efetiva e hash da resposta oficial; o snapshot registra hashes dos arquivos-fonte. Na execução de 13/10, a tabela legada `backend/data/indices/taxa_legal.csv` foi preservada fora do pacote canônico e a regra antiga permaneceu pendente de revisão metodológica. **Revisão posterior, 22/10/2026:** por decisão expressa do usuário, esse CSV e os identificadores antigos de juros e correção foram removidos; os perfis atuais de juros de 1% e Taxa Legal oficial permanecem separados.

Validação: `liquidacao_custom.index_data.validation.validate_directory` aprovada; 9 testes dirigidos de fontes/catálogo aprovados; 16 testes dirigidos de poupança e Civil 3 aprovados (um teste de API/exportações não incluído). A suíte financeira mais ampla foi interrompida em caso de longa duração, portanto não foi declarada aprovada. Os limites do catálogo após a atualização são Fazenda Pública até 30/09/2026, Civil 1 a 5 até 01/10/2026, SELIC/CJF referência 01/10/2026 com taxa de 09/2026, e remuneração de depósitos até a data de consulta, condicionada a aniversários completos.

Pacote local assinado e conferido: `build/indices/indices-v2-20261013T193402808255Z`. ZIP de 136.999 bytes, manifesto de 4.606 bytes, 23 arquivos permitidos. Identidade do conjunto SHA-256: `3b207ce9fcb69f868cfe93969a22e5f2f251a6db437bcce2eab4cc3a0639eb6a`. ZIP SHA-256: `94e576ff967b47fef44501c32abbd3413e7eb4b27c34b7fd4f5af6fa5724fba7`. Assinatura do manifesto verificada com a chave pública configurada; conteúdo do ZIP comparado byte a byte com as bases locais.

## Publicação autorizada em 14/10/2026

Após autorização expressa posterior, foi executado somente `publicar-indices.ps1 -Pacote 'build\indices\indices-v2-20261013T193402808255Z'`. O publicador confirmou assinatura, conteúdo e hashes remotos. A API do GitHub confirmou a release pública `indices-v2-20261013T193402808255Z`, marcada como pré-lançamento, sem rascunho, com apenas `indices-update.json` (4.606 bytes) e o ZIP (136.999 bytes): https://github.com/fabiobarretoadvogado/CalculosJuridicos/releases/tag/indices-v2-20261013T193402808255Z. Nenhum instalador ou código foi publicado nesta ação.
