## Multas por parcela — 17/09/2026

Solicitação: permitir multa em cada parcela principal, com juros sobre a multa. Esclarecimento do usuário: percentual sobre o saldo da parcela.

Implementado exclusivamente nas parcelas de Principal e honorários. Cada parcela possui Multa (%), opcional e inicialmente zero, depois do saldo não editável. O saldo continua sendo valor original menos pagamento no vencimento, antes dos encargos e da multa. Percentuais são individuais, com até quatro casas decimais, entre zero e cem. Não aplicar percentual automaticamente às parcelas existentes.

Multa nominal = (valor original − pagamento no vencimento) × percentual / 100. Arredondar a multa nominal ao centavo por HALF_UP. A multa nominal recebe atualização e juros em operação autônoma, pelos mesmos critérios, datas, termo inicial de juros, contagem e eventual limite EC 136 da parcela. Nos perfis SELIC, preservar a taxa única, sem criar uma segunda incidência de juros. Não alterar as regras das multas das operações de dívida dos honorários sucumbenciais.

O total da parcela inclui seu saldo e encargos mais a multa com os próprios encargos. A coluna Multa e encargos inclui essas três rubricas da multa; atualização e juros do principal permanecem separados. Descontos são abatidos depois e custas são acrescidas ao final, sem integrar a base da multa. Parcela integralmente paga no vencimento não gera multa. Multa omitida ou zero preserva o cálculo anterior.

Resultado e PDF discriminam os valores da multa. O PDF possui tabela própria com multa nominal, bases, períodos, fatores ou taxas e encargos separados por coluna; seus valores já integram a tabela principal e não são novamente somados. Manter um único cabeçalho por tabela e o total financeiro à direita. API, Excel e CSV preservam os detalhes e a memória mensal identificada como multa. O modelo Excel passa a sete colunas, incluindo multa_percentual; o modelo simplificado anterior, de seis colunas, permanece aceito com multa zero.

## Verificação

- 19 testes específicos aprovados: quatro perfis, pagamentos parciais, quitação, multa zero e omitida, percentuais individuais, juros com termo inicial próprio, arredondamento de meio centavo, multa subcentavo, percentual de 100%, rejeição de entradas inválidas, descontos, custas, importação antiga e nova, API, PDF, Excel, CSV e total do resumo PDF à direita.
- 126 testes selecionados de multas, PDF, cálculo simplificado, honorários e descontos aprovados.
- Interface: 21 testes aprovados; verificação estática e build aprovados.
- Build da porta 4173 conferido pelo navegador com a API local atualizada. Parcela de R$ 1.000,00, pagamento no vencimento de R$ 200,00, vencimento em 01/10/2025, multa de 2%, IPCA-E e poupança, data-base 31/08/2026: saldo R$ 800,00; multa nominal R$ 16,00; atualização da multa R$ 0,60; juros da multa R$ 1,22; multa atualizada R$ 17,82. Parcela total R$ 908,60. Custa de R$ 100,00 na mesma data, corrigida exclusivamente por IPCA-E, resultou em R$ 103,75. Total geral R$ 1.012,35.
- No mesmo formulário, multa zero retirou a coluna da multa e gerou total de R$ 994,53, diferença exata de R$ 17,82. Editar a multa invalidou o resultado anterior.
- API local reiniciada e conferida novamente no perfil SELIC/CJF: mesma multa nominal de R$ 16,00, SELIC de R$ 1,83, total da multa R$ 17,83, sem juros adicionais. Metodologia concilia principal, SELIC e multa com encargos.
- Layout amplo: seis campos visíveis na linha da parcela, sem cartões ou novas bordas. A quebra responsiva da linha ocorre abaixo de 900 pixels úteis para acomodar o campo adicional. Em 390 pixels de janela, os campos ficam em uma coluna, com 44 pixels de altura e fonte de 16 pixels. Largura útil e largura de rolagem da página iguais (375 pixels), sem rolagem horizontal. Estados sem parcelas e custas, com parcela e com custa conferidos. Dimensão temporária restaurada; aba de teste fechada sem inserir dados sintéticos na aba do usuário.
- PDF: três exemplos sintéticos, com uma parcela e custa (quatro páginas), vinte parcelas SELIC/CJF (cinco páginas) e trinta e seis parcelas com múltiplos componentes, descrição e observação extensas (oito páginas). Todas as dezessete páginas renderizadas e inspecionadas; páginas afetadas por ajustes finais renderizadas novamente. Colunas alinhadas nas continuações, um cabeçalho por tabela, nenhuma parcela dividida entre páginas e total unido à última linha. Custas em página exclusiva, logo oficial e rodapé preservados. Gerador de QA em tmp/qa_multas_parcelas.py; artefatos sintéticos em tmp/pdfs/multas_parcelas. Nenhum relatório de processo real foi sobrescrito.

## Pendências anteriores e limite da bateria geral

A execução integral foi interrompida na coleta por acesso negado ao arquivo tests/test_ipcae_mensal.py. Excluindo apenas esse arquivo, o resultado foi 188 aprovados e três falhas nos testes existentes da EC 136. Não declarar a bateria completa aprovada. O módulo de valor da causa não foi alterado como parte desta solicitação.

As três falhas também foram reproduzidas com incorporar_multas_parcelas substituída, somente durante a execução diagnóstica, por uma função que devolve o resultado sem alteração. Não são corrigidas nem ocultadas pela implementação da multa:

- test_selic_ate_ec136_nao_aplica_tema905_ou_poupanca_antes_da_transicao: expectativa de 1,3%; resultado de 1,9% nas bases simuladas.
- test_inicio_juros_nao_limita_selic_nem_ipcae: expectativa de R$ 3,00; resultado de R$ 9,00 nas bases simuladas.
- test_mes_corrente_parcial_nao_e_completo: expectativa de cobertura até 30/09/2025; resultado de 31/10/2025 nas bases simuladas.

Essas divergências exigem revisão própria dos cenários simulados e dos critérios já existentes, sem modificar encargos jurídicos para fazer os testes passarem. A validação específica da multa não resolve essas pendências.
