## Honorários por faixas — Fazenda Pública

Implementação de 18/09/2026 na categoria autônoma de honorários por redução de dívida. A base permanece o máximo entre zero e a diferença das duas dívidas atualizadas com encargos independentes. A alteração não muda a categoria principal, os índices, os descontos ou as bases dos acréscimos do art. 523.

## Fonte e aplicação

Lei 13.105/2015, art. 85, §§ 3º a 5º, versão oficial atualizada conferida: https://www2.camara.leg.br/legin/fed/lei/2015/lei-13105-16-marco-2015-780273-normaatualizada-pl.html

| Parcela da base em salários mínimos | Intervalo de percentual |
| --- | --- |
| Até 200 | 10% a 20% |
| Acima de 200 até 2.000 | 8% a 10% |
| Acima de 2.000 até 20.000 | 5% a 8% |
| Acima de 20.000 até 100.000 | 3% a 5% |
| Acima de 100.000 | 1% a 3% |

O escalonamento é progressivo, não uma taxa única correspondente ao valor total. O salário mínimo deve ser o vigente na sentença líquida ou na decisão de liquidação (§ 4º, IV), informado expressamente com marco e data. Não derivar do ano da data-base nem presumir salário oficial. A data da decisão pode ser posterior à data-base dos encargos. A incidência e os percentuais dependem da decisão; mínimos na tela são sugestões explícitas. Não reconhecer automaticamente direito a honorários, inclusive em execução contra a Fazenda Pública.

## Reutilização e contrato

`honorarios_proveito.py` valida o novo contrato e adapta o proveito econômico como base manual ao `calcular_honorarios` existente em `acessorios.py`, com as cinco faixas canônicas de `models.py`. Nenhum limite da faixa é editável. Salário obrigatório e positivo, exatamente cinco percentuais, até quatro casas decimais e limites legais validados inclusive para faixas não alcançadas. Percentual único e escalonamento são mutuamente exclusivos; entradas antigas continuam aceitas.

Arredondamento HALF_UP de cada faixa ao centavo em contexto decimal local, sem mudar o motor legado globalmente. Total dos honorários igual à soma das faixas. Custas/despesas corrigidas apenas por IPCA-E e adicionadas separadamente ao total geral, nunca à base dos honorários. A memória de cada dívida e os critérios SELIC mensais continuam intactos.

API JSON e PDF existentes suportam o novo modo; a categoria autônoma não tinha exportação CSV/Excel, que não foi introduzida nesta alteração. Resultado guarda salário, marco, data, percentuais, limites inferior/superior em salários mínimos, base, percentual e honorários de cada faixa, total, fonte e percentual efetivo diagnóstico. O percentual efetivo não é apresentado como percentual fixado na sentença.

## Interface e relatório

Forma de fixação em `Dados do cálculo`. Percentual único é o padrão. Alternar modos conserva dados e invalida o resultado; `Limpar` restaura o padrão. Grade existente de três colunas em largura ampla, duas até 960 pixels e uma até 700; cinco percentuais usam a grade padrão existente de duas colunas e uma no celular. Sem tokens, cores, bordas, cartões ou breakpoints novos; controles e tipografia compactos/móveis reutilizados.

PDF mantém identidade institucional e resumo em linha, usando `Por faixas` no lugar do percentual único. Discriminação das cinco faixas mantida junta, sem repetição de cabeçalho; se não couber na primeira página, segue integralmente para a seguinte. Custas continuam em página exclusiva e cada dívida conserva sua tabela e critérios. Faixas não alcançadas são indicadas expressamente. Percentuais aplicados conservam até quatro casas decimais no resultado e no PDF.

## Verificações realizadas

- 117 testes de backend passaram: arquivos `test_honorarios_fazenda.py`, `test_honorarios_proveito.py` e `test_honorarios_principais.py`.
- Cobertura de limites exatos e excedentes das cinco faixas, mínimos, máximos, intermediários, arredondamento, base nula/negativa, custas separadas, salário manual sem fallback, marco posterior à data-base, entradas inválidas, modos exclusivos, API JSON/PDF e regressões dos fluxos anteriores.
- 39 testes de renderização da interface passaram; campos obrigatórios, intervalos legais, alternância sem mutação do estado, precisão dos percentuais e cabeçalho único conferidos. Lint sem alertas e build concluído.
- PDF hipotético `output/pdf/exemplo_honorarios_escalonados_fazenda.pdf` gerado e todas as cinco páginas renderizadas e inspecionadas visualmente: sem sobreposições, faixas juntas na página 2, custas exclusivas na página 3, identificação e dívidas preservadas. Valores de salário e decisões meramente demonstrativos, sem aplicar a autos anteriores.
- Demonstração: base R$ 150.000.000,00 e salário artificial de R$ 1.000,00; honorários mínimos progressivos R$ 3.964.000,00. Custas corrigidas pelo motor existente em R$ 249,97, com variação negativa do IPCA-E parcial; total R$ 3.964.249,97.
- Inspeção interativa do navegador em desktop/celular pendente: o acesso ao navegador falhou por erro de permissões do ambiente (`apply deny-read ACLs`). Testes de renderização e reutilização dos breakpoints não equivalem a essa conferência visual. Não se alteraram permissões nem se contornou o isolamento.

Exemplo de entrada: `backend/examples/honorarios_fazenda_escalonados.json`. PDF demonstrativo não é cálculo judicial definitivo e nenhum relatório de processo anterior foi sobrescrito.
