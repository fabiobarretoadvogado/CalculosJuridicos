## Separação de créditos e débitos no PDF — 05/10/2026

O exportador oficial da categoria principal identifica as parcelas como `CRÉDITO - ACRÉSCIMO` e os abatimentos como `DÉBITO - DECRÉSCIMO`. Por revisão expressa do usuário, os blocos podem compartilhar a página, com intervalo de 1,5 cm depois das parcelas, seus históricos complementares e eventuais multas. Se não houver espaço para o intervalo, título, explicações, cabeçalho e primeira linha, o bloco de pagamentos e descontos começa na página seguinte, sem adicionar os 1,5 cm no topo. Sem pagamentos ou descontos, não há intervalo adicional.

Pagamentos desmarcados permanecem identificados como não abatidos, sem gerar tabela de débito fictícia. Custas passam a compartilhar a página com intervalo de 1,5 cm, quando houver espaço para o início completo do bloco. A alteração não modifica o motor, os valores, os critérios, a seleção dos pagamentos ou a conciliação.

## Revisão atual: compartilhamento com 1,5 cm — 05/10/2026

O intervalo entre créditos, débitos e o bloco de custas é de 1,5 cm quando compartilham a página. Custas deixaram de exigir quebra de página: o exportador mede o espaço necessário para título, explicação, cabeçalho e primeira linha (incluindo o total em tabela de lançamento único). Sem espaço, o bloco inicia na página seguinte, sem intervalo adicional no topo. Último lançamento e total ficam juntos. A regra é compartilhada pelos relatórios principal e de honorários.

Validação atual: 206 testes pertinentes aprovados e um teste preexistente de cobertura de índices desmarcado. Esse teste espera cobertura até 31/08/2026, enquanto o conjunto atual chega a 30/09/2026; motor e índices não foram alterados nesta revisão. Três testes de paginação conferem a distância real, a transferência do início completo do bloco e a continuação de 40 custas sem perda de lançamentos ou separação do total.

| Cenário atual | Páginas | Resultado |
| --- | --- | --- |
| Comparativo padronizado | 3 | Créditos e débitos compartilham a página com 1,5 cm |
| Uma parcela SELIC, um desconto e uma custa | 3 | Créditos, débitos e custas na página 2 |
| Vinte parcelas SELIC, dois descontos e uma custa | 5 | Custas iniciam na página 4 por falta de espaço anterior |
| Trinta e seis parcelas com múltiplos componentes, 25 descontos e uma custa | 9 | Custas compartilham a página 7 com o fim dos débitos |
| Uma parcela com histórico e observações extensos, um desconto e uma custa | 6 | Custas compartilham a página 4 |

As 26 páginas desses cinco cenários foram renderizadas com Poppler e inspecionadas visualmente. Os 30 exemplos do catálogo também foram regenerados: 122 páginas de relatórios e duas de índice (124 no caderno), todas inspecionadas. Logo, margens, textos, tabelas, totais e rodapés sem cortes ou sobreposições. Conferidas igualdade dos resultados antes/depois da exportação, integridade dos 92 arquivos do ZIP e identidade do texto e conteúdo de cada página individual com sua posição no caderno; 31 marcadores apontam para as páginas corretas.

Arquivos de conferência atual: `tmp/pdfs/custas-operacoes-15cm/` e `tmp/pdfs/exemplos-todos-modelos/`. Entrega atual: `output/pdf/exemplos-todos-modelos/`, com verificação registrada em `Verificacao_entrega.json`. Nenhum novo instalador foi gerado nesta revisão.

## Validação histórica da separação por páginas

- Antes da alteração: 43 testes de PDF e descontos aprovados.
- Depois da alteração: 48 testes aprovados, incluindo cinco novos cenários de separação e pagamentos desmarcados. Uma advertência de depreciação já existente na dependência do cliente de testes.
- Verificação pelo endpoint oficial `/api/v1/calculo/exportar/pdf`: créditos anteriores aos débitos, sem compartilhamento de página; custas separadas; totais e abatimentos presentes; cabeçalho único por tabela; rodapés e ausência de páginas vazias.
- Quatro exemplos sintéticos renderizados com Poppler e todas as 27 páginas inspecionadas. Logo, cores, margens, alinhamentos, continuação das tabelas, totais e textos extensos preservados, sem cortes ou sobreposições.

| Cenário | Páginas | Créditos | Débitos |
| --- | --- | --- | --- |
| Uma parcela SELIC, um desconto e uma custa | 5 | 3 | 4 |
| Vinte parcelas SELIC, dois descontos e uma custa | 6 | 3 a 4 | 5 |
| Trinta e seis parcelas com múltiplos componentes, 25 descontos e uma custa | 10 | 3 a 5 | 6 a 8 |
| Uma parcela com histórico e observações extensos, um desconto e uma custa | 6 | 4 | 5 |

Exemplo sintético para revisão: `output/pdf/exemplo-creditos-debitos.pdf`. Entradas, demais PDFs, páginas PNG e folhas de contato: `tmp/pdfs/creditos-debitos/`. A validação usou armazenamento isolado, sem gravar cálculos no perfil real ou sobrescrever relatórios de processos.

A alteração está no código do projeto. Não foi gerado nem publicado um novo instalador nesta etapa.
