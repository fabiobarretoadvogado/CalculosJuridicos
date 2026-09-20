## Descontos fora do vencimento — 17/09/2026

Implementado em Principal e honorários, após Parcelas e antes de Custas e despesas processuais. Cada lançamento possui descrição, data e valor. Perfil e marco de juros são independentes das parcelas, como na operação de dívida correta dos honorários. Por padrão, acompanha o perfil das parcelas e inicia os juros na data de cada desconto.

A modalidade atualiza cada desconto até a data-base e abate a soma do total das parcelas atualizadas. Não recalcula o saldo devedor em cada pagamento. Pagamentos no vencimento permanecem separados; um mesmo pagamento não deve ser informado nas duas seções. As custas são acrescidas depois. Qualquer excesso sobre as parcelas é informado, sem compensação automática com custas.

Resultado, PDF, Excel e CSV incluem os descontos, os encargos discriminados, os índices, as bases, os períodos efetivos, a memória mensal própria, a entrada original e a conciliação do total. Sem descontos, os cálculos existentes são preservados. Alterar os descontos invalida o resultado anterior.

## Verificação

- 21 testes específicos de descontos: aprovados, cobrindo os quatro perfis, encargos diferentes, datas próprias, pagamentos no vencimento, custas, limites, excesso, memória, API, PDF, Excel e CSV.
- 116 testes selecionados de descontos, honorários, PDF, cálculo simplificado e SELIC/CJF: aprovados.
- Interface: 18 testes aprovados; verificação estática e build aprovados.
- Conferência no build da porta 4173: parcela de R$ 1.000,00 com R$ 200,00 pagos no vencimento; desconto de R$ 150,00 em 15/10/2025 pela SELIC; custa de R$ 100,00 em 01/10/2025 pelo IPCA-E; data-base 31/08/2026. Parcelas atualizadas R$ 900,99 − desconto atualizado R$ 167,13 + custas R$ 103,75 = R$ 837,61. Editar os encargos retirou o resultado anterior.
- Layout conferido em largura ampla e em 390 pixels: superfície plana, espaçamento compartilhado de 64 pixels, campos móveis de 44 pixels e texto de 16 pixels, sem rolagem horizontal da página.
- PDF: três exemplos sintéticos com 1 parcela, 20 parcelas SELIC e 36 parcelas com múltiplos componentes; todas as páginas renderizadas e inspecionadas. Descontos sem repetição do cabeçalho, sem divisão de lançamento entre páginas, com larguras constantes e total junto da última linha. Custas em página exclusiva. Artefatos de QA em tmp/pdfs/descontos; gerador em tmp/qa_descontos.py. Nenhum relatório de processo real foi sobrescrito.

## Pendências encontradas na bateria geral

Resultado geral: 170 aprovados e 4 falhas em cenários sem descontos. Não alterar esses critérios ou o fluxo de valor da causa como parte desta solicitação.

- test_ipcae_mensal.py::test_deflacao_parcelas_adicionais_sem_nova_correcao_e_pdf: gerador principal procura ipcae_pre, mas o perfil de valor da causa usa componente correcao; KeyError no PDF.
- test_perfis_ec136.py::test_selic_ate_ec136_nao_aplica_tema905_ou_poupanca_antes_da_transicao: teste espera taxa 1,3%; motor usa 1,9% nas bases simuladas.
- test_perfis_ec136.py::test_inicio_juros_nao_limita_selic_nem_ipcae: teste espera R$ 3,00; motor retorna R$ 9,00 nas bases simuladas.
- test_perfis_ec136.py::test_mes_corrente_parcial_nao_e_completo: teste espera cobertura até 30/09/2025; motor retorna 31/10/2025 nas bases simuladas.
