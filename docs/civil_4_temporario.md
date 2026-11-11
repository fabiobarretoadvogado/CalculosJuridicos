# Civil 4 temporário — 06/10/2026

Perfil `civil_4_temporario_v1`, disponível para parcelas, descontos e comparação de dívidas. A inclusão preserva Civil 1/2/3, chaves e registros anteriores. A interface usa os componentes existentes e identifica a opção como **Civil 4 (temporário)**. O PDF descreve os encargos, sem nomes internos dos perfis.

## Termos e fases

Correção começa na data própria de cada parcela; juros começam no termo escolhido (vencimento, citação, data específica ou termo individual, quando disponível no fluxo). O termo dos juros pode anteceder o da correção. Inclui-se o início e exclui-se a data-base em todos os intervalos. A cobertura mínima do perfil é 01/07/2009, limitada também à disponibilidade efetiva de cada série.

Até 29/08/2024:

- Havendo somente correção, aplicar IPCA SGS 433, com fatores geométricos e deflação preservada.
- Havendo somente juros, aplicar SELIC deduzida do IPCA.
- Havendo juros e correção, aplicar SELIC SGS 4390 como índice único, sem IPCA concomitante.

Desde 30/08/2024, aplicar IPCA SGS 433 e Taxa Legal oficial SGS 29543 com os termos iniciais independentes. O marco decorre dos efeitos da Lei 14.905/2024 e é explicitado para a primeira Taxa Legal pela Resolução CMN 5.171/2024, art. 8º, parágrafo único. Não é criado outro marco experimental.

## Convenções escolhidas

A dedução anterior à correção usa os percentuais da **mesma competência**: taxa líquida mensal = máximo entre SELIC mensal menos IPCA mensal e zero. A taxa do trecho é a taxa líquida multiplicada pelos dias efetivamente abrangidos, divididos pelos dias corridos do mês. Não truncar IPCA negativo: deflação aumenta a diferença; a auditoria conserva SELIC, IPCA, diferença original, taxa aplicada e indicação do piso. A fórmula aritmética e seu piso são convenções operacionais do perfil temporário, aprovadas expressamente; o acórdão consultado determina a dedução, sem fixar esses detalhes numéricos. Não se reconstrói SGS 29543 antes de sua existência, nem se atribui essa fórmula à metodologia oficial da Taxa Legal.

SELIC deduzida e SELIC integral acumulam de forma simples **sobre o mesmo capital**, sem consolidar os juros ao passar de uma para a outra. O capital de referência incorpora somente eventual IPCA que tenha incidido antes dos juros. Não aplicar SELIC integral sobre juros líquidos acumulados na fase anterior.

Em **30/08/2024**, consolidar uma única vez o saldo total existente: capital após eventual IPCA anterior mais juros líquidos e atualização SELIC histórica. Por escolha expressa do usuário, esse saldo passa a ser a base tanto do IPCA posterior quanto da Taxa Legal. A nota do demonstrativo é apenas **Base consolidada na transição**. A consolidação não é apresentada como regra de transição fixada pelo AgInt no AREsp 2.059.743, nem inferida automaticamente de precedentes próprios da Fazenda Pública.

A Taxa Legal posterior soma as taxas oficiais proporcionais e aplica a taxa acumulada, com seis casas decimais, à base consolidada corrigida final. Segue a rotina oficial compartilhada de juros simples; não há recapitalização mensal. A correção permanece restrita ao seu termo próprio mesmo que posterior à consolidação. Se não houve encargos antes da transição, a consolidação conserva o principal.

## Precisão, cobertura e memória

IPCA proporcional: fator do trecho = (1 + taxa mensal / 100) elevado à fração de dias corridos. SELIC integral e deduzida usam taxas simples, sem deslocar competências para o mês seguinte. Esse deslocamento pertence ao perfil CJF existente e não é reutilizado aqui. Taxa Legal usa a série oficial, cuja metodologia CMN considera fatores SELIC e IPCA-15 do mês anterior; isso é distinto da dedução histórica acima.

Preservar Decimal e precisão integral até o arredondamento HALF_UP ao centavo. Componentes financeiros são diferenças de saldos arredondados, de modo que principal mais componentes concilie com o total. Juros líquidos anteriores são discriminados no componente `juros_selic_deduzida`; correção de seus valores após a transição pertence ao componente IPCA posterior. SELIC integral é o encargo único da fase correspondente.

O resultado registra os cinco componentes (`ipca_pre`, `juros_selic_deduzida`, `selic`, `ipca_pos`, `taxa_legal`), bases, datas efetivas, memória mensal, taxas brutas, convenções, consolidação e hashes das bases consultadas. Detalhes técnicos ficam em `metodologia_tecnica`, `memoria_selic_civil`, `memoria_taxa_legal` e `memoria_transicao_civil`, conservados no JSON. PDF, Excel e CSV mostram componentes e memória; o PDF usa rótulos curtos, fonte e estilos comuns, sem repetir a justificativa técnica por linha.

SELIC provém exclusivamente da união conciliada de `selic_historica.json`, `indices_simplificados.json` e `indices_ec136.json`, lida pelo leitor canônico. Competências duplicadas iguais são contadas uma vez; divergências bloqueiam o cálculo. Uma competência SELIC ou IPCA ainda não fechada na consulta é bloqueada, inclusive se a data-base abranger apenas parte dela. Ausência de qualquer índice exigido pelo intervalo e taxas inválidas impedem o cálculo. Não estimar taxas, substituir por zero ou converter pacotes antigos. Fontes schema 2, lista de 18 arquivos, registros salvos e limites específicos de custas permanecem preservados.

## Fontes oficiais consultadas

- [Lei 14.905/2024, arts. 1º e 5º](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14905.htm): IPCA, SELIC deduzida da atualização, piso e efeitos da alteração.
- [Resolução CMN 5.171/2024](https://www.bcb.gov.br/content/estabilidadefinanceira/especialnor/Resolu%C3%A7%C3%A3o5171.pdf): metodologia oficial, juros simples/proporcionalidade (art. 6º), base atualizada (art. 7º) e marco 30/08/2024 (art. 8º).
- [STJ — Tema 1.368](https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2025/29102025-Tese-sobre-aplicacao-da-Selic-a-dividas-civis-passa-a-ter-os-efeitos-do-recurso-repetitivo.aspx): SELIC nas dívidas civis antes da nova redação do art. 406.
- [STJ — notícia de 12/03/2025](https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2025/12032025-Selic-deve-ser-aplicada-como-juros-moratorios-se-sentenca-nao-determinar-outra-taxa.aspx) e [inteiro teor do AgInt no AREsp 2.059.743/RJ](https://scon.stj.jus.br/SCON/GetInteiroTeorDoAcordao?dt_publicacao=20%2F02%2F2025&num_registro=202200205552), julgado em 17/02/2025, publicado em 20/02/2025: dedução do IPCA quando incidem somente juros; fundamentos nas páginas 14–16 do PDF.

## Verificação local

`backend/tests/test_civil_4.py` usa exclusivamente índices e operações fictícios em pasta isolada. Cobre IPCA antes da SELIC, juros antes da correção, piso zero e deflação na dedução, ausência de consolidação intermediária, saldo total na transição, corte 29/30 de agosto, termos posteriores ao corte, data-base igual ao termo, datas globais/individuais, índices ausentes, competência parcial, SELIC duplicada, descontos, multa, comparação de dívidas, CSV/Excel/PDF e API/recuperação.

Executar com `backend/.venv/Scripts/python.exe -X utf8 -m pytest` os testes do Civil 4 e as regressões dirigidas de Civil 1, Civil 3 e Taxa Legal. Usar `--basetemp` em um diretório **novo** dentro de `tmp`, para isolar registros e contornar a restrição do temporário global do Windows. A interface é conferida por `npm run build` (TypeScript e Vite). O usuário dispensou suíte completa e exame visual nesta tarefa. Sem instalador, instalação, publicação, commit ou recálculo de casos reais.

Resultado desta execução: 49 testes dirigidos passaram, e TypeScript/Vite compilou. Base oficial consultada em 01/10/2026: termos mínimos em 01/07/2009 e data-base máxima em 01/09/2026, excluída dos encargos.
