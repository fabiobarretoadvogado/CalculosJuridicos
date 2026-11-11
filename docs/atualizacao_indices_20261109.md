# Conferência dos índices em 09/11/2026

As oito séries do BCB/SGS foram consultadas diretamente em 09/11/2026. As respostas completas e seus hashes SHA-256 estão em `build/indices/audit-20261109/`. Todos os registros sobrepostos coincidiram com as bases locais; nenhum valor anterior foi alterado. A [FGV](https://portalibre.fgv.br/press-releases/igp-m-de-outubro-de-2026) confirmou o IGP-M de outubro e o [IBGE](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9260-indice-nacional-de-precos-ao-consumidor-amplo-15.html?edicao=47841) confirmou o IPCA-15 de outubro.

| Série | Base anterior | Novidade confirmada | Fonte |
| --- | --- | --- | --- |
| IGP-M SGS 189 | até 09/2026 | 10/2026: 1,47% | https://api.bcb.gov.br/dados/serie/bcdata.sgs.189/dados?formato=json&dataInicial=01%2F01%2F2020&dataFinal=09%2F11%2F2026 |
| IPCA-15/IPCA-E SGS 7478 | até 09/2026 | 10/2026: 0,32% | https://api.bcb.gov.br/dados/serie/bcdata.sgs.7478/dados?formato=json&dataInicial=01%2F07%2F2009&dataFinal=09%2F11%2F2026 |
| SELIC mensal SGS 4390 | até 09/2026 | 10/2026: 1,07% | https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json&dataInicial=01%2F12%2F2021&dataFinal=31%2F10%2F2026 |
| Taxa Legal SGS 29543 | até 10/2026 | 11/2026: 0,749583% | https://api.bcb.gov.br/dados/serie/bcdata.sgs.29543/dados?formato=json&dataInicial=01%2F08%2F2024&dataFinal=09%2F11%2F2026 |
| Poupança de depósitos SGS 195 | até 09/10/2026 | 25 registros de 10/10 a 06/11/2026 | https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados?formato=json&dataInicial=09%2F12%2F2021&dataFinal=09%2F11%2F2026 |
| Meta SELIC auxiliar SGS 432 | até 13/10/2026 | 27 registros de 14/10 a 09/11/2026 | https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01%2F09%2F2025&dataFinal=09%2F11%2F2026 |

IPCA SGS 433 e INPC SGS 188 permaneceram em 09/2026, sem divergência com as consultas completas de 09/11. A divulgação de 10/2026 está prevista pelo IBGE para 12/11/2026. A SELIC mensal de 11/2026, visível parcialmente na consulta do dia 09/11, foi excluída. Salário mínimo de 2026 e as séries históricas fechadas permaneceram inalterados.

Foram atualizados os JSONs canônicos, as fontes diárias, o snapshot, a série EC 136, os hashes e as datas e URLs de consulta próprias. A poupança tem sua consulta registrada em `poupanca_depositos_fonte.json`; uma consulta de outra série não altera esse campo. Os CSVs antigos em `backend/data/indices/` já estavam removidos antes desta execução, conforme a decisão de 22/10/2026 registrada em `AGENTS.md`; nenhum foi recriado. A antiga tabela `taxa_legal.csv` não foi substituída pela SGS 29543.

Validação: `validate_directory` e `ensure_no_regression` aprovadas contra cópia dos 23 arquivos anteriores; 87 testes dirigidos de índices, poupança e perfis aprovados fora do sandbox. O executor `scripts/test-suite.ps1 -Suite indices` parou antes da execução porque seu inventário ainda não inclui `test_civil_6.py` e `test_indices_historicos.py`. O teste histórico `test_bases_completas_e_conciliadas` falhou: espera IPCA desde 1980 e IPCA-E desde 1992, mas as bases canônicas anteriores e atuais começam em 2009. Essa extensão histórica preexistente requer revisão separada; não se inferiu nem preencheu taxa ausente.

Limites efetivos do catálogo após a atualização: Fazenda Pública e IPCA-E simples até 31/10/2026; SELIC/CJF até a referência de 01/11/2026, com última taxa fechada em 10/2026; Civil 1 a 5 até 01/10/2026, limitados pelo IPCA de 09/2026; depósitos até 09/11/2026, respeitados os aniversários completos e os registros disponíveis até 06/11.

Pacote local preparado exclusivamente com `publicar-indices.ps1 -Preparar`: `build/indices/indices-v2-20261109T135150199011Z`. ZIP de 137.712 bytes; manifesto assinado de 4.606 bytes; 23 arquivos. Dataset SHA-256 `c32f8d0c238a8ad1be68a608feb6f3ccf1dca3808537c0b748f730ecab1ecddd`. A assinatura, a lista fechada, os hashes, os bytes de cada arquivo e a integridade do ZIP foram reconferidos contra as bases locais. A chave de assinatura existente foi usada; nenhuma chave foi gerada ou rotacionada. Nada foi compilado, instalado ou publicado.
