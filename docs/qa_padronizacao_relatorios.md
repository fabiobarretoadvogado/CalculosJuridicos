# Padronização dos relatórios PDF

Validação em 05/10/2026. O pedido foi dar uma estrutura comum aos modelos de cálculo e reunir informações que apareciam em vários pontos, preservando a identidade Barreto Fontes e a separação entre créditos e débitos.

## Revisão atual: grade comum de todas as tabelas

Revisão integral da paginação em 05/10/2026: foram auditados todos os caminhos de geração PDF e os 30 exemplos atuais. Foram removidas as quebras obrigatórias que ainda existiam antes das bases isoladas, faixas, primeira dívida, metodologia e anexo técnico. Essas seções passam a acompanhar a altura disponível, preservando a ordem, títulos e intervalos de 1,5 cm entre blocos de tabelas. Não restam chamadas `PageBreak` nos exportadores; `CondPageBreak` permanece para impedir título ou cabeçalho órfão quando falta espaço.

`tmp/auditar_paginacao_final.py` conferiu o conteúdo dos trinta PDFs, a presença dos créditos na primeira página dos quinze modelos principais, a ausência de páginas vazias e a igualdade integral das entradas e resultados com a revisão anterior. O caderno atual tem 100 páginas, incluindo as duas do índice. A cópia de entrega é `output/pdf/exemplos-todos-modelos/Caderno_exemplos_paginacao_corrigida_05-10-2026.pdf`. O registro atual está em `Verificacao_entrega.json`. Não foram executados testes de suíte nem exame visual nesta revisão; a auditoria foi feita no código e no conteúdo/posicionamento extraído dos PDFs.

Atualização do resumo: rótulo `Principal`, quantias de 10 pontos e total de 12 pontos; margens internas reduzidas para compactar o bloco e acomodar nove métricas em uma única linha quando as quantias couberem. Valores extensos continuam em linhas equilibradas. Catálogo e PDFs de revisão regenerados sem testes ou exame visual, por orientação do usuário.

Atualização de tipografia: toda a seção `CRITÉRIOS E METODOLOGIA` passou a usar 8 pontos, incluindo título, subtítulos, rótulos e corpo, com entrelinha de 11 pontos. Os estilos são locais à seção. O catálogo e os dois PDFs de revisão foram regenerados sem testes ou exame visual, conforme orientação do usuário.

Atualização posterior: retirada a quebra obrigatória entre observações e créditos no demonstrativo principal. A tabela pode começar na primeira página, com 1,5 cm de intervalo, quando couberem título, explicação, cabeçalho e primeira linha. O catálogo e os dois PDFs de revisão foram regenerados sem testes ou exame visual, conforme orientação expressa do usuário. As contagens e verificações anteriores abaixo permanecem históricas.

Atualização posterior em 05/10/2026: os rótulos `Valor informado` foram substituídos por `Valor` na interface, PDF, Excel e CSV. A expressão genérica `até a data-base` foi retirada da apresentação do PDF, mantendo datas e referências finais. A transição de débitos para honorários continua usando a regra condicional de espaço, sem quebra obrigatória. O catálogo foi regenerado com 30 exemplos e 118 páginas. Por orientação expressa do usuário, não foram executados testes nem exame visual nesta atualização; as verificações abaixo correspondem à revisão anterior.

Em 05/10/2026, a conferência da foto apontada pelo usuário confirmou que honorários sucumbenciais, cumprimento e destaque contratual ainda usavam uma grade própria. A revisão alcançou também bases isoladas, faixas, encargos dos honorários fixados, operações de dívida, custas e memórias mensais. Todos esses blocos passaram a usar `tabela_operacional`, em `backend/liquidacao_custom/core/relatorio_layout.py`, junto com créditos, débitos e multas.

O padrão comum usa cabeçalho de 8 pontos em negrito azul-marinho sobre fundo claro, margens internas de 6 pontos nas laterais e 3 pontos na vertical, divisórias cinza de 0,25 ponto, filete cinza de 0,6 ponto sob o cabeçalho e fechamento azul-marinho de 0,6 ponto. O total recebe fundo claro e filete superior; tabelas sem total recebem o filete ao final. Descrições e critérios ficam à esquerda, valores à direita. O cumprimento agora apresenta a soma dos acréscimos de multa e honorários em uma linha de total. Bases e percentuais não são somados. Percentuais das tabelas foram uniformizados em quatro casas, mantendo seis casas para a Taxa Legal e precisão integral no cálculo. Foram conservados o intervalo de 1,5 cm, a paginação condicional, os títulos em maiúsculas e a metodologia em texto.

**Validação:** 294 testes pertinentes aprovados na execução ampla; após os ajustes finais de exibição, os 154 testes afetados passaram novamente. O teste novo confere os traços efetivamente desenhados no PDF, o tamanho da fonte dos valores e o total do cumprimento. Dois testes preexistentes de cobertura foram desselecionados porque esperam agosto, enquanto a base atual informa setembro. Não houve alteração do motor ou dos índices.

Os 30 exemplos foram regenerados. Todas as 116 páginas individuais e as duas páginas do índice foram renderizadas e inspecionadas, sem cortes ou sobreposições. O caderno tem **118 páginas** e 31 marcadores. Os dez casos adicionais de QA totalizam 57 páginas, também inspecionadas: comparativo, créditos/débitos, vinte parcelas SELIC, trinta e seis parcelas multicomponentes, texto extenso, três casos sintéticos de limite ativo, valores extensos e 36 itens de honorários.

`tmp/qa_grades_tabelas.py` reproduz a geração. `tmp/verificar_grades_tabelas_entrega.py` confirmou 30 pares de entradas e resultados JSON iguais aos anteriores, 92 arquivos íntegros no ZIP, os destinos dos marcadores e a identidade das páginas individuais incorporadas ao caderno. O registro atual é `output/pdf/exemplos-todos-modelos/Verificacao_entrega.json`. Os dois PDFs de revisão foram atualizados e o comparativo original foi preservado. A alteração está no projeto e nos exemplos; não foi gerado nem instalado novo pacote desktop nesta etapa.

## Histórico: intervalo comum e paginação de todas as tabelas

Em 05/10/2026, o usuário estendeu a regra de espaçamento a todos os blocos de tabelas. O intervalo de 1,5 cm e o aproveitamento condicional da página agora abrangem multas, honorários principais, cumprimento, destaque contratual, faixas, operações de dívida dos honorários e memórias mensais, além de créditos, débitos e custas. Foram retiradas as quebras obrigatórias antes dos acessórios e entre operações quando há espaço para o próximo início. As tabelas das dívidas deixaram de ser divididas em grupos fixos de oito ou doze itens; continuam pela altura disponível. Títulos, explicações, cabeçalho e primeira linha ficam juntos, assim como a última linha e o total quando possível. Não há intervalo adicional no topo da página. A síntese inicial e o anexo técnico mantêm sua organização.

No exemplo apontado, os honorários sucumbenciais agora ocupam a mesma página dos débitos. Os testes medem o intervalo físico de 1,5 cm após a conciliação e verificam também cumprimento e destaque contratual. Uma operação longa com 36 itens confirma a sequência integral, sem duplicações, a ausência da divisão fixa em oito itens e a continuidade das duas dívidas.

**Validação:** 293 testes pertinentes aprovados: 292 passaram na execução ampla, e o teste novo de tabela longa passou após corrigir sua expectativa sobre a quantidade variável de linhas na primeira página. Os três testes de acessórios foram repetidos com a medição geométrica e passaram. Dois testes antigos de cobertura foram desselecionados: esperam agosto, enquanto a base atual informa setembro. Não houve alteração do motor, dos índices, das entradas ou dos resultados.

Os 30 exemplos foram regenerados, e todas as suas 118 páginas, mais as duas páginas do índice, foram renderizadas e inspecionadas. O caderno passou de 123 para **120 páginas**, com 31 marcadores. Dez casos adicionais de QA totalizam 57 páginas, também inspecionadas: comparativo, exemplo de créditos/débitos, vinte parcelas SELIC, trinta e seis parcelas multicomponentes, texto extenso, três casos sintéticos de limite ativo, valores extensos e 36 itens de honorários. Os casos sintéticos seguem identificados como testes.

`tmp/qa_espacos_tabelas.py` reproduz a geração. `tmp/verificar_espacos_tabelas_entrega.py` confirmou 30 pares de entradas e resultados JSON idênticos aos anteriores, 92 arquivos íntegros no ZIP, destinos dos marcadores e igualdade das páginas individuais incorporadas ao caderno. O registro está em `output/pdf/exemplos-todos-modelos/Verificacao_entrega.json`. Os PDFs de revisão foram atualizados; o comparativo original foi preservado. A alteração está no projeto, sem geração ou instalação de novo pacote desktop nesta etapa.

## Histórico: resumo uniforme e cabeçalhos

Em 05/10/2026, os cinco comentários sobre o caderno foram aplicados aos exportadores oficiais. O resumo financeiro passou a usar um bloco compartilhado em `core/relatorio_layout.py`, com campos de mesma largura, rótulos de 8 pontos e quantias regulares de 12 pontos; o total conserva 14 pontos, azul-marinho e filete amarelo. Os valores ficam alinhados. O exemplo com oito campos cabe em uma única linha, com quebra dos rótulos dentro dos campos. Valores extensos ou uma quantidade maior de campos recebem linhas equilibradas, sem reduzir a fonte nem deixar o total sozinho na última linha. Os resumos das operações de dívida dos honorários seguem o mesmo padrão; as equações próprias da capa foram preservadas.

Os cabeçalhos de créditos, débitos, multas, operações de dívida dos honorários e custas usam `Descrição`. A frase explicativa do sinal `-` foi removida. O complemento genérico `até a data-base` foi retirado dos cabeçalhos dos componentes; períodos específicos de transição, datas efetivas, bases, fatores e taxas foram preservados. Não houve alteração do motor, dos índices, das entradas ou dos resultados. Foram mantidos os valores líquidos pós EC 136/2025, o rótulo `(-) Descontos`, a metodologia em texto, os títulos em maiúsculas e o intervalo de 1,5 cm.

**Validação:** 289 testes distintos pertinentes passaram. A execução abrangente aprovou 288 testes; após o ajuste final de distribuição das linhas e a inclusão de mais um caso, os 116 testes afetados passaram novamente. Dois testes antigos de cobertura foram desselecionados: `test_perfil_ipcae_1am_avanca_ate_o_ultimo_mes_fechado` e `test_fazenda_publica_2_usa_selic_oficial_ate_agosto_de_2026`, que esperam agosto enquanto a cobertura atual informa setembro. Foram conferidos alinhamento, larguras, posição do total, valores extensos, cabeçalhos e ausência de mutação dos resultados.

`tmp/qa_resumo_colunas.py` regenerou os dois PDFs de revisão, os cinco casos obrigatórios, três cenários sintéticos com limite ativo e um cenário com valores extensos: nove casos e 47 páginas, renderizadas e inspecionadas integralmente. Os índices artificiais permanecem exclusivos da verificação. Os 30 exemplos do catálogo também foram regenerados; todas as suas 121 páginas e as duas páginas do índice foram inspecionadas. O caderno conserva 123 páginas e 31 marcadores.

`tmp/verificar_resumo_colunas_entrega.py` confirmou a igualdade integral dos 30 pares de entradas e resultados JSON com o pacote anterior, a integridade das 92 entradas do ZIP, a composição do caderno e a identidade do conteúdo das páginas individuais nele reunidas. O registro final está em `output/pdf/exemplos-todos-modelos/Verificacao_entrega.json`. O comparativo original foi preservado. A revisão está no projeto e nos exemplos; não foi gerado nem instalado novo pacote desktop.

## Histórico: valores líquidos pós EC 136/2025 e rótulo Descontos

Em 05/10/2026, o pedido de retirar “Ajuste ao limite SELIC” foi aplicado à apresentação dos PDFs. O componente compartilhado `core/relatorio_componentes.py` incorpora a redução à correção monetária pós EC 136/2025, seguindo a apuração já existente no motor. O campo e a coluna separados deixaram de aparecer nos resumos e tabelas de créditos, débitos, multas e operações de dívida dos honorários. Os juros e o total são preservados. A metodologia esclarece que os valores são líquidos e que fatores e taxas identificam os índices antes da redução. Os componentes originais continuam nos dados e memórias detalhadas; não houve alteração do motor, das entradas, do JSON, Excel ou CSV.

O resumo passou a usar `(-) Descontos`, e a conciliação usa “descontos”, sem “abatidos”. A seção técnica em blocos de texto, os títulos em maiúsculas e o intervalo de 1,5 cm entre operações foram mantidos.

**Validação atual:** 221 testes pertinentes passaram. Dois testes antigos de cobertura foram desselecionados: `test_perfil_ipcae_1am_avanca_ate_o_ultimo_mes_fechado` e `test_fazenda_publica_2_usa_selic_oficial_ate_agosto_de_2026`, cujas expectativas de agosto divergem da cobertura atual de setembro. Os novos testes verificam limites ativos e inativos, a soma das rubricas líquidas e a ausência de mutação dos resultados, incluindo créditos, multas, descontos e honorários.

O registro reproduzível está em `tmp/qa_pdf_liquidos.py`. Os cinco casos obrigatórios e três casos sintéticos com limite ativo foram regenerados, renderizados e inspecionados em todas as 42 páginas. Os índices artificiais dos três casos adicionais são exclusivos da verificação e não integram a base oficial. Os dois PDFs de revisão têm três páginas cada.

Os 30 exemplos do catálogo foram atualizados. Foram inspecionadas as 57 páginas dos quinze exemplos principais e as duas páginas do índice. As 64 páginas dos demais exemplos de honorários têm conteúdo PDF idêntico à versão anteriormente inspecionada. O caderno final conserva 123 páginas e 31 marcadores. `tmp/verificar_pdf_liquidos_entrega.py` confirmou a igualdade integral das 30 entradas e resultados JSON com o pacote anterior, a integridade dos 92 arquivos do ZIP e a preservação do conteúdo de todas as páginas individuais no caderno. O registro final está em `output/pdf/exemplos-todos-modelos/Verificacao_entrega.json`.

O comparativo original foi preservado, incluindo as ressalvas da simulação na cópia padronizada. A mudança está no projeto e nos exemplos; não foi gerado nem instalado novo pacote desktop. As verificações abaixo registram versões anteriores.

## Histórico: critérios em texto, sem tabela

Em 05/10/2026, após o pedido de retirar a tabela confusa, o componente compartilhado `core/relatorio_criterios.py` passou a apresentar cada operação em um bloco vertical. O título acompanha três linhas alinhadas à esquerda: padrão aplicado, início dos encargos e referência final. As regras exclusivas ficam abaixo da operação correspondente; as idênticas aparecem uma única vez em “REGRAS COMUNS”, com indicação das operações abrangidas. Fontes continuam reunidas ao final e únicas por URL. O corpo técnico conserva Helvetica de 9 pontos e entrelinha de 12, com negrito apenas nos rótulos e títulos. O espaçamento entre as linhas de identificação é de 2 pontos, evitando uma nota isolada sem reduzir a fonte.

O intervalo de 1,5 cm e o aproveitamento condicional da página pelos blocos financeiros foram mantidos. Não houve mudança do motor, índices, entradas, resultados ou ressalvas. Os novos testes conferem o alinhamento das linhas e a posição das regras exclusivas e comuns nos relatórios principal, Civil 1 e de proveito econômico.

**Validação atual:** 209 testes pertinentes passaram; um teste de cobertura preexistente foi desselecionado, pois espera 31/08/2026 e a base atual informa 30/09/2026. Os cinco casos obrigatórios foram regenerados, renderizados e conferidos em todas as 26 páginas: exemplo de créditos/débitos (3), comparativo (3), vinte parcelas SELIC (5), trinta e seis parcelas com vinte e cinco descontos (9) e texto extenso (6). O registro reproduzível está em `tmp/qa_criterios_texto.py`.

Os 30 exemplos do catálogo também foram atualizados e todas as suas 121 páginas, mais as duas páginas do índice, foram inspecionadas. O caderno final tem 123 páginas e 31 marcadores. A integridade das 92 entradas do ZIP, as páginas e destinos do caderno, a igualdade integral das entradas e resultados JSON com o pacote anterior e a preservação das páginas financeiras foram confirmadas por `tmp/verificar_criterios_texto_entrega.py`. O registro final está em `output/pdf/exemplos-todos-modelos/Verificacao_entrega.json`.

Os PDFs de revisão e o catálogo em `output/pdf/` refletem essa revisão. O comparativo original foi preservado. A alteração está no projeto; não foi gerado nem instalado novo pacote desktop nesta etapa. Os números e a tabela descritos nas verificações históricas abaixo correspondem às versões anteriores.

## Histórico: primeira simplificação de critérios e metodologia

Após a aprovação da análise, a seção técnica passou a usar `core/relatorio_criterios.py` em ambos os exportadores oficiais. O quadro inicial identifica operação, padrão, início dos encargos e referência final. Regras idênticas são explicadas uma vez, com indicação das operações abrangidas; diferenças efetivas permanecem separadas. Custas e acessórios têm seus próprios âmbitos. Extinção integral não recebe índice ou encargo fictício, e honorários sem juros não exibem termo inicial ausente.

Corpo e células técnicas usam Helvetica de 9 pontos e entrelinha de 12; o negrito fica nos rótulos e títulos. Fontes oficiais permanecem únicas por URL, no final. Foram retirados os avisos de cobertura máxima do programa do PDF, preservando limites e validações na aplicação, referência mensal SELIC e última competência efetivamente usada. No Civil 1 e Civil 2, o quadro explicita a exclusão da data-base dos encargos. A nota genérica de citação/segunda incidência da SELIC foi dispensada porque a regra de índice único já a esclarece.

**Validação atual:** 334 testes passaram e um teste antigo de cobertura foi excluído dessa execução; após o último ajuste de espaçamento, os 41 testes de PDF, contrato comum e Civil 1 passaram. O teste de cobertura foi executado isoladamente e a falha anterior foi confirmada: espera 31/08/2026, enquanto a base atual informa 30/09/2026. Os testes financeiros, a ausência de mutação do resultado, o compartilhamento de regras, os termos distintos, o índice aplicado e a fonte regular de 9 pontos foram conferidos. Não houve alteração de motor ou índices nesta simplificação.

Foram regenerados 13 exemplos, totalizando **73 páginas**, renderizadas e inspecionadas: comparativo (4), exemplo de créditos/débitos (5), principal com acessórios (7), Civil 1 (7), redução de dívida (5), faixas (6), extinção (5), valor da causa (4), valor certo nominal (2), valor certo com encargos (5), vinte parcelas SELIC (6), trinta e seis parcelas com vinte e cinco descontos (10) e texto extenso (7). A inspeção incluiu tabelas, continuações, fontes, margens e rodapés. O registro reproduzível está em `tmp/qa_criterios_enxutos.py` e o inventário em `tmp/pdfs/criterios-enxutos/manifest.json`.

Os dois PDFs de revisão foram atualizados em `output/pdf/`. Valores, entradas, ressalvas e chaves de recuperação foram preservados. A mudança está no projeto e nos exportadores; não foi gerado ou instalado novo pacote desktop nesta etapa.

## Estrutura comum

1. Cabeçalho institucional com modalidade, data-base e chave de recuperação, quando existente.
2. Resumo financeiro ou equação da modalidade, seguido dos dados do processo.
3. Observações e ressalvas antes das operações, com continuação quando o texto exigir.
4. Operações financeiras em blocos identificados: créditos e débitos; dívida original e correta; base escolhida dos honorários; acessórios e custas, conforme aplicáveis. Todos os blocos de tabelas podem compartilhar a página com intervalo de 1,5 cm quando couber o início do próximo bloco.
5. Uma seção de critérios e metodologia, identificando a operação a que cada regra pertence.
6. Memórias mensais em anexo técnico, quando existentes.
7. Uma seção final de fontes, com URLs únicas e indicação das operações que as utilizam.

`core/relatorio_layout.py` concentra documento, estilos, cabeçalho, identificação, observações, custas, fontes e rodapé. Os exportadores oficiais principal e de honorários usam esses mesmos blocos. As fórmulas específicas são conservadas: redução de dívida, valor da causa, valor certo, valor certo com encargos e faixas da Fazenda. Não há operação fictícia para modalidades inaplicáveis.

As memórias do valor da causa e dos encargos dos honorários ficam depois das operações. A tabela de custas é a mesma nas duas categorias. Rótulos de IPCA-E são preservados e as taxas da Taxa Legal são apresentadas com seis casas decimais. A logo mantém largura de 122 pontos e a proporção original; há verificação da geometria da imagem no PDF.

## Comparativo fornecido

O original `Comparativo_parcelas_e_debitos_01-09-2026.pdf` foi preservado. A entrada foi obtida do arquivo `Entradas_e_ressalvas_dos_calculos.json` que o acompanha, sem reconstruir valores pela aparência do PDF. A cópia revisada foi gerada pelo motor e exportador oficiais em `output/pdf/Comparativo_parcelas_e_debitos_01-09-2026_padronizado.pdf`.

| Item conferido | Valor preservado |
| --- | --- |
| Data-base informada | 01/09/2026 |
| Créditos atualizados | R$ 169.579,26 |
| Contrapartida comparativa atualizada | R$ 317.306,53 |
| Excedente da comparação | R$ 147.727,27 |
| Abatimento limitado às parcelas | R$ 169.579,26 |
| Saldo matemático exibido | R$ 0,00 |
| Chave original | CJ1-8454-6EB0-6880-42C2-E472 |

A cópia tem quatro páginas: síntese e ressalvas; créditos; débitos e conciliação; critérios e fontes. A observação original foi conservada integralmente, incluindo o caráter de simulação, a ausência de pagamentos ou quitação e a ressalva de que o zero não significa extinção da dívida. A omissão técnica de R$ 1,00, os documentos mencionados e a ausência da transição da Lei 14.905/2024 continuam declarados. A alteração é visual e estrutural; não constitui revisão jurídica dessas premissas.

## Verificação anterior à simplificação técnica

Foram executados os testes de PDF, descontos, honorários por proveito, bases isoladas, valor certo, faixas, acessórios principais e IPCA/Taxa Legal: **250 passaram e um falhou**. A mesma falha já ocorria antes da alteração: `test_perfil_ipcae_1am_avanca_ate_o_ultimo_mes_fechado` espera cobertura até 31/08/2026, enquanto a base atual informa 30/09/2026. O motor e os índices não foram alterados para fazer esse teste passar. Após o último ajuste de rótulos, os 18 testes de PDF e contrato compartilhado passaram.

Os testes novos verificam ordem comum, localização das ressalvas, seção técnica única, fontes sem URLs duplicadas, logo proporcional, margens/formato/rodapé, preservação do resultado durante a exportação e tratamento do excedente sem converter comparação em quitação. Os testes financeiros existentes preservam valores esperados.

Todos os exemplos abaixo foram gerados pelos exportadores oficiais e tiveram todas as páginas renderizadas e inspecionadas, incluindo continuações, totais, margens, tabelas, logo e rodapés.

| Exemplo | Páginas |
| --- | --- |
| Comparativo fornecido | 4 |
| Principal com honorários sobre valor da causa e custas | 7 |
| Civil 1 com Taxa Legal, honorários e custas | 7 |
| Honorários por redução de dívida | 5 |
| Honorários por faixas da Fazenda | 6 |
| Extinção integral expressamente informada | 5 |
| Honorários sobre valor da causa | 4 |
| Honorários de valor certo nominal | 2 |
| Honorários de valor certo com encargos | 5 |
| 20 parcelas SELIC | 6 |
| 36 parcelas com múltiplos componentes e 25 descontos | 10 |
| Observações e histórico extensos | 7 |
| Total | 68 |

A página de observações pode continuar além da síntese quando o conteúdo for extenso. As páginas de cada operação podem ter espaço livre em cálculos curtos; a separação é intencional. Não foi aplicado limite artificial de páginas ou redução da fonte para compactar informações.

## Comentário sobre o exemplo de créditos e débitos

O arquivo `output/pdf/exemplo-creditos-debitos.pdf` também foi regenerado pelo exportador oficial a partir de sua entrada sintética original, em resposta ao comentário sobre a antiga página 4. A versão anterior foi preservada em `tmp/pdfs/comentario-debitos/exemplo-creditos-debitos-anterior.pdf`. O exemplo atualizado tem cinco páginas: síntese, créditos, débitos, custas e seção técnica com fontes. A página de débitos não contém listas de fontes nem blocos de critérios ou metodologia. Total geral de R$ 1.689,52, abatimento de R$ 11,14 e crédito de R$ 1.596,91 foram conferidos contra o PDF anterior. Todas as cinco páginas foram renderizadas e inspecionadas; os nove testes de PDF passaram. O teste de separação agora também verifica a ausência de links e dos blocos técnicos na página de débitos.

## Entrega e alcance

Os quatro títulos principais indicados na revisão do exemplo foram colocados em maiúsculas: `VALORES POR PARCELA - CRÉDITOS`, `DESCONTOS ATUALIZADOS - DÉBITOS`, `CUSTAS E DESPESAS PROCESSUAIS` e `CRITÉRIOS E METODOLOGIA`. A alteração está nos exportadores oficiais, incluindo custas e critérios da categoria de honorários, e no contrato visual. O exemplo foi regenerado e suas cinco páginas inspecionadas; a comparação textual, ignorando diferenças de caixa, confirmou que o conteúdo permaneceu igual.

As mudanças estão no código-fonte e no contrato do projeto (`AGENTS.md` e `README.md`). Os exemplos hipotéticos são apenas material de verificação. Nenhum instalador foi gerado ou publicado; o programa instalado só receberá o novo padrão depois de empacotar e instalar a atualização.

## Ampliação para todos os títulos de seção

Todos os títulos de seção e subseção dos relatórios principal e de honorários agora são apresentados em maiúsculas pelos estilos compartilhados `secao`, `secao_tabela` e `tecnico_titulo`. A regra também alcança observações, históricos complementares, memórias, anexos, acessórios e fontes, inclusive títulos dinâmicos. O título de capa, os textos explicativos e os cabeçalhos de coluna mantêm a apresentação anterior. A transformação ocorre na apresentação do PDF, preservando os dados e as fórmulas.

Os 236 testes distintos pertinentes passaram após adequar as expectativas de texto à nova caixa; a suíte de faixas foi novamente executada após corrigir a busca do título e seus 39 testes passaram. O teste de cobertura mensal já identificado acima foi excluído desta execução, sem alterar o motor ou os índices. As verificações incluem títulos em maiúsculas e preservação da caixa do corpo do relatório.

Os 13 exemplos foram regenerados pelos exportadores oficiais, renderizados e inspecionados em todas as 73 páginas. As quantidades de páginas permaneceram iguais, sem cortes ou sobreposição nos títulos mais longos. O manifesto desta conferência está em `tmp/pdfs/todos-titulos-maiusculos/manifest.json`. Os dois PDFs de entrega foram atualizados e os totais financeiros conferidos permaneceram iguais.

## Nomes das operações de crédito e débito

Por solicitação expressa, os títulos da tabela de parcelas e da tabela de abatimentos passaram a ser, respectivamente, `CRÉDITO - ACRÉSCIMO` e `DÉBITO - DECRÉSCIMO`. O exportador oficial, o contrato visual, a documentação atual e as verificações de PDF usam os novos nomes. A separação de páginas permanece igual.

Foram regenerados e inspecionados cinco exemplos, totalizando 32 páginas: comparativo, uma parcela, 20 parcelas SELIC, 36 parcelas com múltiplos componentes e textos extensos. A comparação integral do texto com os exemplos anteriores confirmou que somente os dois títulos mudaram; valores, ressalvas, períodos, fontes, chaves e quantidade de páginas foram preservados. Manifesto em `tmp/pdfs/credito-acrescimo-debito-decrescimo/manifest.json`.

Na execução ampliada, 224 testes passaram inicialmente. Cinco verificações ainda esperavam a caixa ou a organização anteriores e foram adequadas ao contrato atual; as duas suítes afetadas passaram integralmente na nova execução (49 testes). No total, 229 testes distintos passaram. A única falha remanescente é a expectativa antiga de cobertura em `test_fazenda_publica_2_usa_selic_oficial_ate_agosto_de_2026`: espera 31/08/2026, enquanto a base atual informa 30/09/2026. Nenhum índice ou regra financeira foi modificado nesta alteração de títulos.

## Compartilhamento de página com intervalo de 2 cm

O usuário revisou a exigência de páginas distintas e fixou intervalo de 2 cm entre o fim do bloco de créditos e o início dos pagamentos e descontos. O exportador permite o compartilhamento da página quando cabem o intervalo, título, explicações, cabeçalho e primeira linha do próximo bloco. Caso contrário, muda de página, sem repetir o intervalo no topo. Históricos complementares e multas continuam antes dos débitos; custas e acessórios conservam as páginas próprias.

A distância foi confirmada pela geometria do PDF: 56,6929 pontos entre a borda final da tabela e o topo da linha do título, equivalentes a 2 cm. O teste de limite de página confirma título, cabeçalho e primeira linha juntos, sem espaço adicional no topo da nova página. A execução conjunta teve 144 testes aprovados e uma falha inicial na medição entre linhas de base, que incluía o espaço interno dos textos; após medir as bordas dos blocos, os 11 testes de PDF passaram integralmente. Total de 145 testes distintos aprovados, abrangendo PDF, contrato compartilhado, descontos, multas e honorários principais.

Os cinco cenários visuais obrigatórios foram renderizados e inspecionados em todas as 29 páginas. O comparativo passou de quatro para três páginas; o exemplo de uma parcela, de cinco para quatro; o exemplo de 20 parcelas, de seis para cinco. Os exemplos de 36 parcelas e de textos extensos mantiveram dez e sete páginas. Valores, entradas, ressalvas e chaves de recuperação foram preservados. Manifesto: `tmp/pdfs/intervalo-operacoes-2cm/manifest.json`. Os dois PDFs de entrega foram atualizados.
## Atualização de 06/10/2026: padronização entre exportadores

Revisão posterior de transições: Anexo técnico, Fontes e conferência e Históricos complementares passaram a usar o intervalo comum de 1,5 cm, suprimido no topo da página. O anexo reserva título, introdução e primeira linha de sua primeira memória, sem duplicar o intervalo inicial. As fontes podem continuar em outra página sem obrigar todas as referências a ficarem juntas. Os 30 exemplos foram regenerados; o caderno atual tem 100 páginas. Não foram executados testes ou exame visual nesta revisão.

Revisão posterior de larguras: todas as tabelas operacionais dos PDFs agora passam por `distribuir_larguras`. O auxiliar mede títulos, palavras e conteúdo com as fontes existentes; reserva espaço para Descrição/Rubrica, prioriza acréscimos pequenos para títulos de uma linha e destina a sobra às colunas textuais. A soma das larguras é preservada. As memórias com altura explícita recalculam o conteúdo após redistribuição, mantendo os mínimos de segurança. Os 30 modelos e os dois PDFs de revisão foram regenerados, assim como o pacote de exemplos; o caderno permanece com 98 páginas. Sem testes ou inspeção visual nesta revisão, por orientação do usuário.

A revisão alcançou os dois exportadores PDF (principal e honorários, inclusive bases isoladas, operações de dívida, acessórios e memórias), Excel, CSV e o relatório textual. Os rótulos apresentados usam Principal, Descrição, Data nos descontos e Descontos. Os nomes dos índices nas memórias são abreviados pelo mesmo auxiliar dos PDFs. A apresentação de componentes no Excel e no resumo CSV reutiliza os componentes líquidos do PDF, sem coluna separada de ajuste ao limite SELIC; as planilhas detalhadas de índices conservam os componentes originais, e o pacote CSV inclui resultado.json completo para conferência. Os nomes internos de perfis continuam nos dados auditáveis, mas não são acrescentados aos cabeçalhos ou dados gerais dos relatórios.

Os PDFs reutilizam metodologia de 8 pontos, explicações curtas de débitos e custas, tabelas comuns e intervalo de 1,5 cm antes da metodologia; não há PageBreak obrigatório. Os exemplos agora descrevem os critérios pelo índice e encargos, inclusive no catálogo e nas observações fictícias, em vez de nomes internos. Excel usa cabeçalhos e células com fonte e identidade comuns para todos os perfis; CSV permanece um formato de dados, sem paginação ou linhas vazias para representar espaçamento.

Foram gerados 30 modelos PDF em um caderno de 98 páginas e 15 conjuntos de Excel, CSV e Markdown para os modelos principais, pelos exportadores existentes. As categorias próprias de honorários têm rota de exportação PDF; esta revisão não criou exportadores Excel/CSV novos para elas. O registro em Verificacao_entrega.json descreve apenas esta geração. Não foram executados testes nem exame visual nesta atualização, conforme orientação do usuário. Não houve publicação ou atualização do aplicativo instalado.


## Correção de Base e Fator nas células — 06/10/2026

A distribuição comum de larguras agora reserva espaço para os grupos completos Base + número, Fator + número e R$ + valor, com a fonte existente. O conteúdo preferencial é medido por linha explícita, evitando que a concatenação das linhas de um componente consuma a largura dos seguintes. A regra atende aos dois exportadores PDF.

O cálculo Giap foi reexportado do resultado original salvo, em conexão somente leitura, sem recálculo ou alteração da origem: chave CJ1-D9DC-6372-11BB-D689-2439, total R$ 61.523,50. A cópia corrigida tem cinco páginas; o original permanece preservado. A extração de texto da cópia e dos 30 exemplos encontrou 266 grupos Base/Fator com número na mesma linha e nenhuma quebra entre esses rótulos e os números. O caderno regenerado tem 100 páginas; os dois PDFs de revisão e o pacote de exportações também foram atualizados. Não foram executados testes ou exame visual. Esta correção posterior à versão 1.15 ainda não foi instalada ou publicada.
