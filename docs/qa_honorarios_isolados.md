## Honorários isolados — extensão de 18/09/2026

Registro da versão inicial. A limitação de equidade a valor já na data-base foi ampliada posteriormente, ainda em 18/09/2026, a pedido expresso: ver [Atualização do valor certo](qa_honorarios_valor_certo_atualizado.md). As notas e valores abaixo documentam o estado inicial, não os limites da versão atual.

Pedido: adicionar equidade (valor certo) e valor da causa na aba Honorários. A ampliação das bases é expressamente solicitada; o padrão anterior de redução de dívida e sua API permanecem compatíveis.

## Critérios e limites

Valor da causa corresponde à quantia ao tempo do protocolo, corrigida apenas por IPCA-E TJSP ou IPCA oficial SGS 433, conforme escolha, sem juros, até a data-base. Aplica-se depois o percentual da decisão, ou as faixas progressivas da Fazenda Pública usando o salário mínimo e marco informados. Custas não integram a base; o valor da causa nunca é somado ao total dos honorários.

Equidade reutiliza a semântica já existente no fluxo principal: valor certo dos honorários já na data-base. Sem novo arbitramento, percentual, juros ou correção automáticos. Não estima valores da OAB nem examina cabimento de equidade, que depende da decisão. Atualização posterior de quantia originalmente fixada em outra data não foi solicitada com seus termos e encargos nesta extensão; continua como operação futura que exige definição expressa. O CPC prevê juros de quantia certa desde o trânsito em julgado (§ 16), que não são presumidos nem calculados neste modo de valor já na data-base.

Fonte oficial conferida, art. 85, §§ 3º a 5º, 8º, 8º-A e 16: https://www2.camara.leg.br/legin/fed/lei/2015/lei-13105-16-marco-2015-780273-normaatualizada-pl.html

## Reutilização e contrato

- Motor: `honorarios_isolados.py` utiliza `corrigir_valor_causa` de `honorarios_principais.py`, o acessório `calcular_honorarios` e o adaptador compartilhado `apurar_faixas_fazenda` extraído sem alterar a aritmética da redução de dívida.
- Campos do protocolo/índice e memória da correção reutilizam `HonorariosCausaCampos` e `HonorariosPrincipaisResultado`. Os componentes anteriores continuam funcionando no cálculo principal.
- API: novas rotas JSON e PDF `/api/v1/honorarios/isolados`; categoria `honorarios_sucumbenciais_isolados`, base `valor_causa` ou `valor_certo`. Campos estranhos e cumulações inaplicáveis são rejeitados. Não criar dívida ou parcela fictícia.
- Protocolo deve estar entre 01/07/2009 e a data-base. Cobertura final segue somente o índice escolhido e, quando houver, a cobertura IPCA-E das custas. Valor certo sem custas não depende dos índices das dívidas ocultas.
- Estado preservado ao alternar bases e invalidação de resultado a qualquer edição; campos ocultos não enviados. Modo equidade não recebe percentual ou escalonamento persistido de outra modalidade.
- Custas permanecem operação autônoma IPCA-E, sem juros e sem incidência na base. Total geral é honorários mais custas atualizadas.

## Interface e PDF

Sem CSS, tokens, cores, bordas ou breakpoints novos. Reutilizadas as grades existentes, tipografia compacta e espaçamento comum. Campos de valor da causa ficam em três colunas em largura ampla, duas até 960 pixels e uma até 700 pixels. A identificação continua como primeiro bloco, permanentemente visível.

O PDF institucional agora recebe os resultados antigos e novos. Valor da causa apresenta uma linha visual valor no protocolo mais correção, igual à base atualizada, seguida do percentual ou indicação de faixas, e dos honorários. Equidade apresenta somente o valor certo com indicação de ausência de nova atualização automática. Não imprimir dívidas ou proveito econômico fictício. Memória mensal da causa em página própria, um cabeçalho por tabela, com competência, índice, base, fator, valor corrigido, período e critério. Custas conservam página exclusiva.

## Validação

- 149 testes de backend passaram nos arquivos de honorários isolados, Fazenda, proveito econômico e honorários principais. Incluem equivalência exata com o resultado principal em IPCA-E/IPCA, valor certo sem encargos, faixas sobre base corrigida, custas separadas, dados incompatíveis, datas, cobertura, memória extensa, JSON/PDF e regressões.
- 42 testes de renderização da interface passaram: seleção das três bases, campos aplicáveis, limites por índice, preservação dos dados, payload sem campos ocultos e fluxos anteriores. Lint sem alertas, build concluído.
- Serviço local reiniciado e conferido: JSON e PDF das duas novas modalidades responderam HTTP 200 com os mesmos valores e páginas dos exemplos. A API e o PDF anteriores de redução de dívida com cinco faixas continuaram respondendo HTTP 200. Preview do build em 4173 respondeu HTTP 200 e carregou o pacote atualizado `index-B9R9dHaU.js`.
- Todas as páginas dos dois exemplos novos foram renderizadas e inspecionadas: valor da causa, 3 páginas; equidade, 2 páginas. Logo, cores, resumo, metadados, bases, memória, cabeçalhos únicos, alinhamentos e páginas exclusivas de custas preservados; sem sobreposições ou cortes visíveis.
- Exemplo hipotético da causa: R$ 10.000,00 em 01/09/2025, IPCA-E até 31/08/2026, base R$ 10.424,35, 20%, honorários R$ 2.084,87; custas R$ 260,61, total R$ 2.345,48.
- Exemplo hipotético de equidade: valor já na data-base de R$ 1.500,05; custas R$ 260,61; total R$ 1.760,66.
- Nenhum PDF ou dado de processo anterior foi sobrescrito. Exemplos expressamente demonstrativos.
- Conferência interativa desktop/celular pendente: navegador falhou na inicialização com erro do helper do ambiente (`node_repl kernel exited unexpectedly` / `orchestrator_helper_report_read_failed`). Não se alteraram permissões nem se contornou o isolamento. Testes de renderização não equivalem à inspeção visual da tela.

Saídas: `output/pdf/exemplo_honorarios_isolados_valor_causa.pdf` e `output/pdf/exemplo_honorarios_isolados_equidade.pdf`. Entradas demonstrativas em `backend/examples/honorarios_isolados_*.json`. PNGs intermediários em `tmp/pdfs/honorarios_isolados_qa/`.
