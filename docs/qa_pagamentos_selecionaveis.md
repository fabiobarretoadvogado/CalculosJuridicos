## Função geral do programa - 18/09/2026

Solicitação: permitir assinalar pagamentos/créditos a abater, sem limitar a função ao processo 0072089-11.2024.8.25.0001.

Reaproveitado o bloco Descontos da categoria Principal e honorários e sua operação autônoma de atualização. Não criado motor exclusivo de processo nem alteradas as bases da categoria autônoma de honorários. Campo `aplicar`, verdadeiro por padrão e também em entradas antigas; desmarcar conserva entradas, exclui índices e abatimento e não limita a cobertura da conta ativa. Data/valor podem ficar em branco somente nos itens desmarcados. A edição invalida o resultado anterior. O resumo pré-cálculo soma somente pagamentos marcados, em valores nominais.

Campo opcional `encargos_sem_atualizacao`: parte do total pago que o usuário expressamente exclui de nova incidência. Não há composição presumida. Base dos encargos = total pago - parte nominal; abatimento atualizado = base atualizada + parte nominal. Validar parte não negativa nem superior ao total. Zero preserva o comportamento anterior; todo o pagamento pode ser nominal quando sua base atualizável é zero. Não repetir pagamento no vencimento, abater um resgate do mesmo depósito ou compensar excedente com custas.

Tela e PDF mostram base e encargos próprios; JSON mantém seleção/composição e memória. Excel acrescenta Pagamentos registrados; CSV acrescenta pagamentos_registrados.csv, incluindo lançamentos não selecionados. Os demais arquivos de índices e memória contêm somente os descontos ativos. Preservada segurança de strings literais no Excel. Não alterados os breakpoints, campos anteriores, identidade, fontes ou cores do projeto. Composição fica recolhida; checkbox reutiliza fee-toggle e campos usam cost-line/grades existentes. Total do PDF alinhado à direita conforme contrato institucional.

## Caso que motivou a extensão

Fonte original preservada: C:/Users/fabio/Downloads/202411802540.pdf, 95 páginas; SHA-256 54A049F9FAB6E20C5FDE9837CB3A290188F70ED708F8C26C482DF9AFC8BC311A. Processo 0072089-11.2024.8.25.0001 / 202411802540, 18ª Vara Cível de Aracaju; Fábio Augusto Mendonça Barreto contra Estado de Sergipe.

Original: R$ 5.800,00 fixados em 14/11/2024, p. 17-18. Recalculado desde esse original, e não desde saldo ou total de conta anterior. Página 90 e solicitação do usuário: pagamento bruto R$ 5.845,82 em 31/12/2025, líquido R$ 5.313,93 mais IR retido R$ 531,89. Conservar a distinção dos comprovantes: depósito de 30/12/2025 e retenção comprovada por ordem de 14/01/2026. A data considerada no abatimento é a expressamente indicada, 31/12/2025.

Página 92 discrimina o pagamento em principal R$ 5.800,00 e SELIC já apurada R$ 45,82. Registrada essa composição explícita, sem aplicar SELIC novamente sobre os R$ 45,82. A antiga conta é fonte da composição do pagamento, não do novo principal ou de saldo artificial. Não lançado o resgate posterior como outro pagamento.

## Conciliação na referência 01/09/2026

| Rubrica | Valor |
| --- | --- |
| Principal original | R$ 5.800,00 |
| SELIC do crédito - 11/2024 a 08/2026, 24,15% | R$ 1.400,70 |
| Crédito integral atualizado | R$ 7.200,70 |
| Pagamento bruto em 31/12/2025 | R$ 5.845,82 |
| Base atualizável do pagamento | R$ 5.800,00 |
| SELIC do pagamento - 12/2025 a 08/2026, 10,18% | R$ 590,44 |
| Encargos pagos abatidos nominalmente | R$ 45,82 |
| Abatimento total na referência final | R$ 6.436,26 |
| Saldo | R$ 764,44 |

O saldo conserva apenas a diferença de SELIC anterior ao pagamento do principal; não se capitaliza esse saldo como um novo principal. Sem custos, nova sucumbência, multa ou destaque contratual. O relatório integral anterior permanece preservado e não é o saldo devedor.

Conferência independente da série oficial BCB SGS 4390 em 18/09/2026: 22 competências do crédito somam 24,15%; as nove do pagamento somam 10,18%; agosto 1,09%. URL: https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json&dataInicial=01/11/2024&dataFinal=31/08/2026. Consulta direta da API oficial confirmou os dados; o leitor web não acessou esse JSON.

Entrada reproduzível: backend/examples/processo_0072089-11.2024.8.25.0001_com_abatimento.json. Resultado estruturado e PDF em output/pdf/calculo_0072089-11.2024.8.25.0001_com_abatimento.*. A API real gerou o PDF pelo mesmo endpoint usado no botão do programa. Memórias: 22 registros do crédito e nove do pagamento.

## Verificação e pendência

226 testes de backend aprovados nos módulos de descontos, SELIC/CJF, simplificado, multas, honorários principais, Taxa Legal e PDF; 47 testes de frontend aprovados, incluindo eventos de marcar/desmarcar sem perda de campos. Tipagem, lint e build concluídos. Cobertos pagamentos parciais, seleção parcial, todos desmarcados/incompletos, parte nominal total/parcial, composição inválida, múltiplos perfis, entradas antigas e exportações. Regressões do relatório abrangem uma, vinte e trinta e seis parcelas e textos longos, inclusive seleção e composição opcionais; total à direita verificado por coordenadas.

PDF final: três páginas renderizadas e todas inspecionadas após o ajuste final. A4 horizontal, logo e paleta preservadas, metadados corretos, tabelas com um cabeçalho, valores alinhados, sem cortes ou sobreposições, rodapés/paginação completos. Página 3 é a seção de fontes, não página vazia.

Build atualizado servido em http://127.0.0.1:4173/processamento, assets index-_RTtRWRI.js e index-C9Ed3MZB.css. Servidor da API atualizado em 8000. Pendência específica: inspeção visual interativa da tela em larguras ampla e móvel não executada, pois Computer Use/CUA falhou na inicialização (`apply deny-read ACLs` e encerramento do kernel), inclusive após uma reinicialização. Não contornada a barreira do ambiente. Os testes de renderização e eventos passaram, mas não substituem essa inspeção visual.
