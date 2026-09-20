# Cálculos Jurídicos — escopo inicial simplificado

O aplicativo aplica exclusivamente os critérios definidos para este projeto:

- **Fazenda Pública 1**: IPCA-E e poupança a partir de 01/07/2009.
- **Fazenda Pública 2**: IPCA-E e poupança até 08/12/2021; SELIC a partir de 09/12/2021.
- **Fazenda Pública 3**: IPCA-E e poupança até 08/12/2021; SELIC de 09/12/2021 a 09/09/2025; IPCA-E e poupança a partir de 10/09/2025.
- **Fazenda Pública 4**: IPCA-E e poupança até 08/12/2021; SELIC de 09/12/2021 a 09/09/2025; IPCA-E e juros simples de 2% ao ano, limitados à SELIC quando inferior, a partir de 10/09/2025.
- Perfil **SELIC**: SELIC simples em todo o período informado.
- **Civil 1**: correção pelo IPCA oficial e juros simples pela Taxa Legal oficial do BCB, com datas independentes.
- **Civil 2**: correção pelo IPCA oficial e juros de mora simples de 1% ao mês, também com datas independentes.

Além da atualização ordinária de parcelas, a aba **Honorários** permite cálculo isolado por **proveito econômico (redução de dívida)**, **valor da causa atualizado** ou **equidade (valor certo)**.

## Honorários isolados — valor da causa e equidade

Selecione `Base dos honorários` em `Dados do cálculo`. Valor da causa recebe o valor no protocolo, a data e IPCA-E ou IPCA, com correção exclusiva até a data-base, sem juros, seguida de percentual único ou das faixas da Fazenda Pública. Reutiliza exatamente o cálculo da tela principal; o valor da causa não é acrescido aos honorários. Resultado e PDF guardam fator, correção, fonte e memória.

Equidade / valor certo permite atualizar a quantia originalmente fixada: informe valor, data da fixação, IPCA-E ou IPCA e os juros. Correção desde a fixação; pelo art. 85, § 16, CPC, os juros começam no trânsito em julgado, em campo independente que não é preenchido por presunção. Juros pela Taxa Legal mensal oficial (desde 30/08/2024) ou percentual mensal simples informado conforme a decisão; neste último, escolha meses inteiros ou dias corridos / 30,4368, reutilizando a contagem existente. Não cumula SELIC integral com os juros. Permite não incluir juros por opção expressa. Custas não integram a operação. Tela e PDF discriminam bases, períodos, fatores, taxas, correção e juros, com memória própria. Exemplo hipotético: `backend/examples/honorarios_equidade_atualizada.json`.

A alternativa expressa `Valor já na data-base` permanece sem nova incidência, evitando atualizar a quantia duas vezes; entradas antigas sem `encargos_valor_certo` conservam esse comportamento. A aplicação não arbitra honorários nem substitui o valor judicial ou os critérios dos §§ 8º e 8º-A do art. 85. O modo de valor certo da tela principal permanece como antes. Registro desta extensão: [Atualização do valor certo](docs/qa_honorarios_valor_certo_atualizado.md).

As novas bases não exigem dívidas. Alternar preserva campos e invalida resultados, mas envia somente os dados aplicáveis. Custas continuam exclusivamente IPCA-E, fora da base e em página própria. `POST /api/v1/honorarios/isolados` calcula; `POST /api/v1/honorarios/isolados/exportar/pdf` gera o relatório. Exemplos hipotéticos: `backend/examples/honorarios_isolados_valor_causa.json` e `backend/examples/honorarios_isolados_equidade.json`. Regras e validações: [Honorários isolados](docs/qa_honorarios_isolados.md).

## Honorários sucumbenciais sobre redução de dívida

Em `Dados do cálculo` da aba `Honorários`, a forma de fixação pode ser **Percentual único** (padrão) ou **Faixas · Fazenda Pública (art. 85)**. O segundo modo reutiliza o cálculo progressivo existente: cada percentual incide somente na parcela da base dentro de sua faixa, com limites e intervalos do art. 85, § 3º, CPC. É necessário informar o salário mínimo vigente na sentença líquida ou na decisão de liquidação, a data e os cinco percentuais; o salário não é inferido pelo ano da data-base. Os mínimos inicialmente sugeridos na tela devem ser confirmados conforme a decisão. Custas e despesas permanecem fora da base e em página própria no PDF. Não se presume a incidência de honorários pelo simples fato de uma parte ser Fazenda Pública.

O JSON aceita alternativamente `percentual_sentenca` ou `escalonamento_fazenda` com `salario_minimo`, `marco`, `data_decisao` e `percentuais_faixas` (cinco percentuais na ordem legal). Não cumular os modos. Resultado e PDF discriminam bases e valores por faixa. Exemplo **hipotético**, sem salário oficial ou vínculo com autos: `backend/examples/honorarios_fazenda_escalonados.json`. Registro de fontes e testes: [Escalonamento da Fazenda Pública](docs/qa_honorarios_fazenda.md).

Esta categoria executa duas operações independentes na mesma data-base:

1. atualiza o valor da dívida originalmente exigida;
2. atualiza o valor correto da dívida;
3. calcula o proveito econômico pela diferença positiva entre os dois valores atualizados;
4. aplica sobre o proveito econômico o percentual fixado na sentença.

Cada dívida possui seu próprio valor, data de origem, padrão de encargos e termo inicial dos juros. Assim, a dívida originalmente exigida e a dívida correta podem usar critérios diferentes, sem mistura das respectivas memórias de cálculo.

Quando a obrigação tiver sido integralmente extinta, marque **Dívida integralmente extinta** na coluna **Dívida correta**. O saldo remanescente será considerado `R$ 0,00` sem exigir item, data ou valor fictício. Os campos anteriormente preenchidos ficam preservados para eventual desmarcação, mas não entram no cálculo; resultado e PDF registram expressamente a extinção sem aplicar correção, juros ou multa à dívida correta.

A fórmula é: `honorários = máximo entre zero e (dívida original atualizada - dívida correta atualizada) × percentual da sentença ÷ 100`.

Quando a diferença não é positiva, o sistema preserva a diferença apurada, atribui zero ao proveito econômico e aos honorários e emite alerta para conferência humana. Honorários sobre o valor da causa e equidade são modalidades alternativas, sem envolver esta comparação. Valor da condenação, prestações vincendas e atualização posterior dos próprios honorários não foram introduzidos nesta extensão.

O endpoint `POST /api/v1/honorarios/proveito-economico` devolve os dois resultados atualizados, encargos apurados, componentes, memória mensal, critérios, fontes, proveito econômico e honorários sucumbenciais.

Custas e despesas processuais podem ser lançadas individualmente com nome, data e valor. Elas são sempre atualizadas exclusivamente pelo IPCA-E, sem juros, não integram o proveito econômico nem a base dos honorários e são somadas aos honorários apenas na composição do total geral devido.

Os arquivos `backend/examples/custas_despesas_principal.json` e `backend/examples/custas_despesas_honorarios.json` documentam entradas completas para os dois fluxos, com valores expressamente demonstrativos.

No PDF de honorários, cada dívida apresenta os encargos efetivamente aplicados em colunas próprias. Cada célula discrimina o período de incidência, a base de cálculo, o fator ou a taxa acumulada e o valor acrescentado à parcela; a linha final concilia o valor informado, os totais de cada encargo e o valor atualizado. A metodologia informa a forma de acumulação e o tratamento de juros, correção e multa sem repetir premissas equivalentes. O primeiro bloco após o cabeçalho reúne toda a apuração em uma única equação horizontal: dívida originalmente exigida menos dívida correta, igual ao proveito econômico, multiplicado pelo percentual da sentença, igual aos honorários, sem repetir o proveito econômico.

As datas são as informadas pelo usuário para este escopo; o aplicativo não decide a aplicabilidade de uma tese jurídica a outros casos.

## Fluxo

1. Em **Principal e honorários**, o primeiro bloco mantém partes, número do processo e observações sempre visíveis. Em seguida vêm a data final, os critérios, as parcelas, os descontos, os honorários sucumbenciais, o cumprimento de sentença e as custas e despesas. Cada parcela exibe descrição, vencimento, valor original, pago no vencimento e saldo automático não editável, antes da atualização monetária. O termo inicial individual dos juros aparece abaixo quando selecionado o critério por parcela. Em largura ampla, os campos ficam na mesma linha; em áreas estreitas, são distribuídos para preservar a leitura.
2. Ao calcular, o resultado aparece ao final da mesma tela: confira o total e os valores por parcela e use **Baixar PDF**. Critérios, fontes, memória mensal e outros formatos ficam disponíveis em seções recolhidas abaixo do resultado. Alterar qualquer dado invalida o resultado anterior; os endereços antigos `/conferencia` e `/exportacao` redirecionam para `/processamento`.

No programa instalado, os downloads abrem o diálogo nativo do Windows para escolher o nome e a pasta de destino. Isso se aplica aos relatórios PDF e às demais exportações disponibilizadas na interface.
3. Na seção de parcelas, **Adicionar parcela** e **Importar Excel** ficam juntos. A importação abre o modelo e o seletor de planilha logo abaixo dessa linha de ações, sem uma divisória expansível separada. As parcelas importadas são acrescentadas às já cadastradas.

O bloco **Descontos**, após **Parcelas**, permite abatimentos com descrição, data e valor próprios. Cada lançamento é atualizado até a data-base, com perfil e início dos juros independentes, como na comparação entre dívidas dos honorários. Por padrão, acompanha o perfil das parcelas, mas os juros começam na data de cada desconto. O pagamento no vencimento continua separado: não lance o mesmo valor nos dois lugares.

Use **Adicionar pagamento ou desconto** e marque **Abater este pagamento** nos lançamentos a considerar. Desmarcar conserva os dados, mas não aplica índices nem altera o saldo; somente os marcados entram no total informado e nos limites de cobertura. Em **Composição do pagamento (opcional)**, informe a parte já paga que não deve receber nova incidência. A base da atualização será o total pago menos essa parte, exibida em campo não editável; a parte excluída será abatida nominalmente. Zero mantém a atualização integral do pagamento. Não presumir essa composição: use os documentos ou critérios do caso. Entradas antigas continuam aplicadas por padrão. A seleção e a composição constam também no PDF, JSON, Excel e CSV. Essa função reutilizável pertence à tela **Principal e honorários**, inclusive quando o crédito principal são honorários fixados em valor certo.

O total das parcelas atualizadas menos os descontos atualizados forma o saldo; os honorários e acréscimos selecionados são apurados depois, e as custas são acrescidas separadamente. Essa modalidade compara operações na data-base, não recalcula o saldo devedor em cada data de pagamento. Caso os descontos superem as parcelas, o abatimento fica limitado à dívida e o excedente é informado, sem compensação automática com custas. Resultado, PDF, Excel e CSV preservam as entradas, os índices, os períodos, os encargos por coluna e a memória mensal própria dos descontos.

Para estimar a remuneração de um depósito judicial ainda não liberado, selecione **Poupança — remuneração da conta** no perfil de **Descontos**. O valor destinado à conta recebe os fatores oficiais SGS 195, por aniversários mensais completos, com reinvestimento; depósitos nos dias 29, 30 e 31 começam no dia 1 do mês seguinte. Não há pró-rata, correção adicional nem juros moratórios nesse abatimento. Em **Composição do pagamento**, a **Parte fora da conta, sem remuneração** retorna nominalmente ao abatimento, permitindo discriminar IR retido sem remunerá-lo. Disponível para depósitos novos desde 04/05/2012. A dívida mantém seu próprio perfil. Não presume quitação no depósito nem a aplicabilidade automática do Tema 677: conferir o saldo real no extrato e recalcular na efetiva entrega. Registro do caso, fontes e validações: [Depósito remunerado pela poupança](docs/qa_poupanca_deposito.md).

Na tela principal, **Honorários sucumbenciais** é um bloco opcional com três bases. **Valor da causa atualizado** parte do valor informado na data do protocolo, corrigido somente por IPCA-E ou IPCA até a data-base, sem juros, seguido da aplicação do percentual. Os índices são distintos e possuem fontes e memória próprias. **Proveito econômico** é o total atualizado das parcelas, com multa individual, após descontos e sem custas. **Valor certo** é o valor dos honorários já na data-base, sem nova atualização automática. A categoria autônoma de redução de dívida permanece independente.

**Cumprimento de sentença** permite escolher separadamente a multa de 10% e os honorários de 10% do art. 523, § 1º, CPC/2015. As duas rubricas usam exclusivamente o crédito das parcelas atualizado após descontos, sem honorários da sentença, custas ou despesas. Os honorários da sentença nunca integram essa base, independentemente de sua modalidade, mas continuam somados ao total devido em rubrica própria. O campo legado `incluir_sucumbenciais_base` é aceito apenas para compatibilidade e normalizado para `false`, sem efeito de inclusão. Não há incidência dos honorários do art. 523 sobre sua própria multa nem presunção automática do decurso do prazo. O **Destaque de honorários contratuais (%)** fica separado: não aumenta o cálculo, não abate a dívida e nunca incide sobre custas ou despesas. Sua base pode ser o crédito da parte, incluindo eventual multa do art. 523 e excluindo honorários judiciais, ou o total sem custas, mediante seleção expressa.

Regras, fontes e validações destes blocos estão em [Honorários principais e cumprimento](docs/qa_honorarios_principais.md). O resultado, PDF, Excel e CSV discriminam bases, percentuais e valores; a correção do valor da causa tem memória mensal própria.

As duas categorias usam 64 pixels de separação entre os blocos principais, após a introdução e antes do resultado, mantendo os campos e fontes compactos. Esse padrão também se aplica à tela móvel.

Na categoria principal, a faixa anterior ao cálculo destaca o principal após pagamentos e as custas informadas com fundo claro, valores em azul-marinho e botão de calcular, sem contorno ou sombra. São valores de entrada, ainda não atualizados; as rubricas permanecem separadas.

Os campos de `Dados do cálculo` compartilham uma única grade: atualizar até, padrão, início dos juros e sua data condicional. Em largura útil acima de 820 pixels, ficam na mesma linha; abaixo disso passam para duas colunas, e em janelas de até 700 pixels, para uma coluna. O perfil SELIC/CJF mantém somente os dois campos aplicáveis.

`Ver os critérios aplicados` fica ao final de `Dados do cálculo`, antes das parcelas. Essa área reúne o aviso de até quando há índices completos e as explicações sobre encargos, início dos juros, períodos, proporcionalidade e fontes. As notas usam fonte de 11 pixels e cada período aparece seguido de dois-pontos e sua regra na mesma linha, com quebra natural no celular. Os limites e erros da data-base continuam funcionando no campo, sem repetir o aviso abaixo dele.

Nos quatro perfis da Fazenda, o termo inicial dos juros respeita o vencimento. A poupança incide apenas nas faixas indicadas pelo perfil; a SELIC reúne atualização e mora; na Fazenda Pública 4, os juros simples de 2% ao ano incidem a partir de 10/09/2025. O pagamento opcional continua limitado ao próprio vencimento.

O PDF é gerado pelo próprio backend, a partir do mesmo motor de cálculo, em A4 horizontal. Apresenta dados do processo, resumo financeiro, observações, valores por parcela, custas e despesas processuais, critérios e fontes consultáveis. Cada tabela possui um único cabeçalho, exibido somente no início, e as páginas de continuação preservam as mesmas larguras e alinhamentos das colunas. As páginas são numeradas. Pagamentos e datas de juros diferentes do vencimento são identificados por parcela. Quando houver custas e despesas, sua tabela ocupa página exclusiva e exibe nome, data, valor original, fator IPCA-E, correção e valor atualizado. A memória mensal completa permanece no Excel, CSV e arquivo de texto. O PDF das 36 parcelas do exemplo ocupa quatro páginas. O demonstrativo reúne bases, índices acumulados, acréscimos, períodos, critérios e fórmulas de conferência, sem remeter a planilhas para demonstrar os valores. As bases são exibidas com quatro casas decimais; o cálculo conserva a precisão integral.

O resultado e o PDF separam os componentes conforme o perfil escolhido. Na Fazenda Pública 4, são exibidos IPCA-E e poupança até 08/12/2021, SELIC de 09/12/2021 a 09/09/2025, IPCA-E e juros simples de 2% ao ano posteriores, além do eventual ajuste ao limite SELIC. Cada coluna mostra o índice acumulado e o acréscimo em reais por parcela. Período não incidente é identificado separadamente de uma taxa zero.

O resultado da API inclui `componentes` por parcela, com datas efetivas, base de cálculo, fator ou taxa acumulada e valor. O resumo inclui `totais_componentes`. As bases e índices mantêm sua precisão integral. Para conciliar centavos sem mudar o total calculado, os valores de atualização por componente são diferenças dos saldos arredondados; a poupança pós é a diferença entre o total de juros arredondado e a poupança pré arredondada. Excel e CSV incluem a memória desses componentes, além dos trechos mensais.

A interface e o relatório seguem a identidade visual da Barreto Fontes usada no CRM: branco, superfícies claras, azul-marinho e detalhes amarelos. Os arquivos da marca são locais e acompanham o aplicativo. No celular, a navegação fica no topo e os valores por parcela aparecem em cartões. A referência visual não cria integração nem dependência com o CRM. O contrato visual obrigatório do PDF, incluindo formato, paleta, tipografia, posições, alinhamentos, tabelas, rodapé e verificação visual, está registrado em `AGENTS.md`, na seção `Diretrizes Visuais Permanentes do PDF`.

A importação Excel utiliza um modelo de sete colunas, disponível no formulário, incluindo `multa_percentual`. O modelo simplificado anterior, de seis colunas, continua aceito sem multa. Planilhas genéricas antigas com índices ou outros critérios são rejeitadas explicitamente. Parcelas importadas são adicionadas às existentes com numeração sequencial.

Cada parcela principal possui **Multa (%)**, opcional e inicialmente zero. A multa nominal é o percentual sobre o saldo após o pagamento no vencimento, arredondado ao centavo (HALF_UP). Ela acompanha a atualização e os juros da própria parcela, inclusive o termo inicial de juros informado, as transições e o eventual limite EC 136, sem duplicar a SELIC. O saldo não editável do formulário permanece anterior à multa e aos encargos. A coluna **Multa e encargos** soma multa nominal, atualização e juros próprios; o demonstrativo PDF discrimina suas bases, índices, períodos e valores em tabela própria, com um único cabeçalho e continuidades alinhadas. API, Excel e CSV preservam esses dados e a memória mensal identificada como multa. As rubricas de atualização e juros do principal permanecem separadas dessa coluna, sem dupla contagem. Descontos são abatidos depois das parcelas com multa e custas não compõem sua base. A regra não altera a multa das operações de dívida na categoria de honorários sucumbenciais.

Regras, exemplos verificados e pendências da validação estão registrados em [Multas por parcela](docs/qa_multas_parcelas.md).

Não há seleção manual de índices para custas e despesas: essa rubrica usa obrigatoriamente o IPCA-E. Também não há taxas manuais de atualização ou juros, regimes privados ou astreintes neste fluxo inicial. Os componentes genéricos antigos do backend permanecem internos, com seus testes, para eventual evolução; as rotas públicas usam somente o modelo e o motor simplificados.

## Critérios civis com datas independentes

Na tela **Principal e honorários**, selecione **Civil 1** ou **Civil 2**. Informe o **Início da correção** na parcela e o termo inicial dos juros por data específica, citação ou individualmente. O termo inicial dos juros não é limitado pela data da correção nesses perfis. O mesmo padrão está disponível para descontos e para as operações de comparação de dívidas dos honorários.

Ambos usam IPCA oficial **SGS 433**, distinto do IPCA-E. O **Civil 1** usa Taxa Legal mensal oficial **SGS 29543**, publicada segundo a [Resolução CMN 5.171/2024](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=5171&tipo=resolu%C3%A7%C3%A3o+cmn). O **Civil 2** usa juros de mora simples de 1% ao mês, proporcionais aos dias corridos, sem capitalização.

Neste perfil, incluem-se os termos iniciais e exclui-se a data-base, conforme a [Calculadora do Cidadão](https://www3.bcb.gov.br/CALCIDADAO/publico/metodologiaCorrigirPelaTaxaLegal.do?method=metodologiaCorrigirPelaTaxaLegal). O IPCA usa fatores geométricos proporcionais aos dias corridos; os juros usam a soma simples de taxa mensal × dias / dias do mês. A taxa acumulada aplicada conserva seis casas decimais e incide sobre o principal corrigido final, com precisão integral até o arredondamento financeiro HALF_UP. Deflações são mantidas.

Os termos iniciais devem ser a partir de **30/08/2024**; períodos anteriores exigem outro critério expresso. O snapshot consultado em **17/09/2026** contém Taxa Legal até setembro/2026 e IPCA até agosto/2026; como a data-base é excluída, a data-base máxima comum é **01/09/2026**, utilizando os índices até 31/08/2026. Índices ausentes não são estimados. O cálculo não depende de consulta à internet.

Tela, PDF, Excel e CSV discriminam IPCA e Taxa Legal por coluna, com bases, datas efetivas e encargos. O PDF inclui a memória mensal da Taxa Legal; Excel e CSV têm memória própria das taxas oficiais, frações e juros. As premissas guardam as entradas e hashes dos dois snapshots. O caso fornecido, a metodologia e a validação estão em [IPCA e Taxa Legal](docs/qa_ipca_taxa_legal.md); a entrada reproduzível está em `backend/examples/processo_3005719-41.2026.8.06.0297.json`.

## Convenções de cálculo

A **Fazenda Pública 4** aplica IPCA-E e poupança até 08/12/2021, passa à SELIC única de 09/12/2021 a 09/09/2025 e, a partir de 10/09/2025, aplica IPCA-E e juros simples de 2% ao ano, com comparação ao limite SELIC do mesmo período.

Revisão `tema905_ipcae_ibge_poupanca_total_v4`: substitui os fatores do TJSP pelas variações mensais oficiais do IPCA-15 produzidas pelo IBGE e distribuídas na série SGS 7478. Mantém a faixa do Tema 905 desde julho/2009 e a remuneração total da poupança. Resultados de versões anteriores precisam ser recalculados porque a fonte e a precisão do IPCA-E foram alteradas.

Este perfil cobre a faixa de IPCA-E e poupança do [Tema 905/STJ](https://processo.stj.jus.br/repetitivos/temas_repetitivos/pesquisa.jsp?cod_tema_final=905&cod_tema_inicial=905&novaConsulta=true&tipo_pesquisa=T), aplicável às condenações administrativas e de servidores nessa faixa temporal. Não implementa todos os ramos do Tema 905 nem as faixas anteriores a julho/2009.

Convenções de contagem, preservada a divisão na transição de critérios:

- Nos perfis da Fazenda, intervalos incluem o primeiro e o último dia. Em setembro/2025, os perfis 3 e 4 aplicam SELIC de 1 a 9 e o regime posterior de 10 a 30, sem sobreposição. Os perfis Civil 1 e Civil 2 incluem o início e excluem a data-base.
- Em dezembro/2021, o Tema 905 incide de 1 a 8 e a SELIC de 9 a 31. Juros de poupança não integram a base da SELIC. O principal corrigido pelo IPCA-E até 08/12/2021 passa a ser a base da SELIC simples.
- Meses incompletos usam dias corridos divididos pelos dias reais do mês.
- SELIC: acumulação **simples** das taxas mensais da série BCB SGS 4390, proporcionais aos dias, sobre o principal corrigido até 08/12/2021 ou o principal apurado para vencimentos posteriores. A data de juros opcional não separa nem posterga a SELIC única.
- IPCA-E: `(1 + variação mensal do IPCA-15 / 100) ^ fração de mês`, sobre o principal no Tema 905 e sobre o saldo consolidado ao fim da SELIC no período posterior. O IPCA-E é a acumulação do IPCA-15; os fatores mensais são multiplicados e as deflações são preservadas.
- Poupança: juros **simples** pela **remuneração total publicada pelo Banco Central (SGS 25 até 03/05/2012 e SGS 195 desde 04/05/2012)**, sobre o saldo consolidado corrigido até a data-base, preservando a convenção do motor existente de juros sobre o valor corrigido final. A série já compõe a remuneração básica e adicional. O rateio diário previamente definido é preservado: taxa mensal da referência dividida pelos dias do mês. Para os dias 29, 30 e 31, usa-se a referência do dia 1 do mês seguinte, conforme a convenção de aniversário da poupança. As referências e os códigos SGS constam na memória; valores ausentes não são estimados.
- A rubrica **Atualização** inclui SELIC única e IPCA-E; **Juros da poupança** contém os juros anteriores a 09/12/2021 e posteriores a 09/09/2025, sem juros sobre juros da poupança.
- Valores são calculados com Decimal e arredondados por parcela, ao final, pelo critério HALF_UP. As memórias exibem centavos; fatores intermediários não são arredondados.
- Vencimentos anteriores a 01/07/2009 estão fora do escopo deste perfil. A data-base não pode anteceder o vencimento. A falta de índice impede a conclusão; nenhuma taxa é substituída por zero.

Essas convenções ficam visíveis na interface e são preservadas nos arquivos exportados. O rateio diário é uma premissa do aplicativo; não é apresentado como instrução de rateio publicada pelo IBGE. Deve ser conferido com o título judicial antes da adoção em um caso real.

## Índices e cobertura

Base consultada em **20/09/2026**, arquivada em `backend/data/indices_simplificados.json`, com fontes originais em `backend/data/fontes/`:

- SELIC mensal: Banco Central, SGS 4390, com série histórica até dezembro/2020 e série corrente de dezembro/2021 a agosto/2026; a mesma fonte alimenta o período posterior à EC 136.
- IPCA-15/IPCA-E produzido pelo IBGE e distribuído pelo Banco Central na série SGS 7478: variações mensais até agosto/2026.
- Remuneração total da poupança: Banco Central, SGS 25 (01/07/2009 a 03/05/2012), SGS 195 (04/05/2012 a 08/12/2021, em dois arquivos) e SGS 195 (01/09/2025 a 06/09/2026). Os arquivos originais preservam taxa, data inicial e data final de cada período publicado. A antiga série de meta SELIC permanece apenas no arquivo histórico de fontes e não alimenta este cálculo.

O limite é específico de cada padrão. Os quatro perfis da Fazenda Pública aceitam data-base até **31/08/2026**; Fazenda Pública 2 agora usa a SELIC oficial até agosto/2026. Os perfis SELIC, Civil 1 e Civil 2 aceitam **01/09/2026**, pois nesses critérios a data-base é uma referência mensal ou é excluída, de modo que o último índice efetivamente usado é o de agosto/2026. Operações combinadas, como honorários, custas e descontos, adotam o menor limite aplicável e informam na tela qual critério o definiu.

O campo de data e o botão de cálculo bloqueiam datas posteriores; a API aplica o mesmo bloqueio ao cálculo e às exportações, inclusive em chamadas diretas. A interface e o PDF distinguem a data-base máxima do último dia ou competência efetivamente utilizados. O limite avança somente quando a base recebe todos os índices necessários, e essa consulta precisa terminar antes de habilitar o cálculo.

Datas posteriores aos limites atuais exigem os índices oficiais das competências seguintes, ainda ausentes no snapshot. O aplicativo não projeta índices nem usa rateio para estender a cobertura de um mês incompleto. O rateio nos períodos cobertos, inclusive a divisão de setembro/2025 entre os dias 9 e 10, permanece preservado conforme orientação do usuário.

A fonte numérica da SELIC é a série mensal 4390 do Banco Central. Não confundir taxa mensal, taxa acumulada e meta anual.

Para atualizar a base, obtenha os documentos oficiais, confira as competências e atualize o script `backend/data/fontes/gerar_snapshot.py` (requer pypdf). O script valida pontos de controle e registra hashes das fontes. Ajuste as datas e verificações à nova publicação; não altere índices isoladamente sem fonte. Não há consulta à internet durante o cálculo.

## Executar localmente

Backend, na pasta `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn liquidacao_custom.api.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, na pasta `frontend`:

```powershell
npm.cmd run dev
```

Abra http://127.0.0.1:5173. A API está em http://127.0.0.1:8000/docs.

## Validar

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest -q
# frontend
npm.cmd run lint
npm.cmd run build
```

Os testes cobrem a transição, dias-limite, ano bissexto, acumulação simples, variações mensais do IPCA-15/IPCA-E, deflação, início dos juros, índices ausentes, rejeição de critérios antigos, importação e consistência das exportações.

## API

`POST /api/v1/calculo`, `/calculo/exportar/pdf`, `/calculo/exportar/excel` e `/calculo/exportar/csv` recebem o mesmo modelo restrito. A exportação PDF retorna `application/pdf`, com download `relatorio_calculo.pdf`, e aplica os mesmos bloqueios de datas e índices ausentes do cálculo. Campos de critérios antigos produzem erro de validação; não são ignorados silenciosamente. `GET /api/v1/criterios` informa perfil, fontes e cobertura.

Exemplo:

```json
{
  "perfil": "selic_ipcae_poupanca_v1",
  "dados_gerais": {"data_base": "2025-09-30"},
  "parcelas": [{
    "numero": 1,
    "historico": "Parcela de exemplo",
    "data_vencimento": "2025-09-01",
    "valor_bruto": "1000.00",
    "valor_pago_na_data": "0.00",
    "data_inicial_juros": null
  }]
}
```

Com o snapshot atual, total de R$ 1.011,78: atualização de R$ 7,03 e juros da poupança (remuneração total) de R$ 4,75. Trata-se de um exemplo técnico das convenções acima.

O uso permanece local. Ainda não há autenticação, armazenamento persistente de cálculos ou homologação com casos reais; recarregar a página descarta os dados não exportados.

## Aplicativo para Windows

O projeto também pode ser distribuído como programa instalado, com interface própria e atualizações assinadas pelo GitHub Releases. O rodapé exibe permanentemente **Verificar atualização**; quando houver nova edição publicada, a ação muda para **Atualizar para…** e conduz o download e a instalação. O controle continua acessível em janelas estreitas. O procedimento completo está em [Publicação e atualizações](Publicacao-e-atualizacoes.md).
