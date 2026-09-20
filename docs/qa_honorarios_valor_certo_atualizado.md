## Atualização dos honorários isolados em valor certo — 18/09/2026

O usuário esclareceu que a quantia fixada também recebe correção e juros; confirmou disponibilizar Taxa Legal oficial e percentual mensal simples. Extensão limitada à aba autônoma Honorários. A tela principal, o proveito econômico, o valor da causa e os relatórios anteriores mantêm seus critérios.

## Distinção dos marcos

Correção monetária desde a fixação. O art. 85, § 16, CPC dispõe que, em quantia certa, juros moratórios incidem a partir do trânsito em julgado da decisão, não da fixação. Há campos independentes; o programa não comprova nem presume trânsito. Usuário informa o marco conforme a decisão. Não arbitrar quantia por equidade nem consultar tabela OAB automaticamente.

Fonte primária conferida: https://processo.stj.jus.br/jurisprudencia/externo/informativo/?livre=%40CNOT%3D018936

## Entradas, reutilização e encargos

- Novo `encargos_valor_certo` inclui fixação, índice IPCA-E/IPCA, regime simples/Taxa Legal/sem juros, início dos juros e percentual mensal simples com contagem aplicável.
- `honorarios_valor_certo.py` reutiliza `corrigir_valor_causa`, as rotinas neutras `calcular_juros` e `contar_meses`, e `apurar_juros_taxa_legal`, extraída sem alteração da aritmética oficial do perfil IPCA + Taxa Legal.
- Taxa Legal SGS 29543: seis casas, proporcionalidade por dias corridos do mês, inclui início e exclui data-base, base corrigida final com precisão integral, soma simples e sem SELIC duplicada. Só desde 30/08/2024; ausência de índice não recebe taxa substituta. A correção de quantia fixada anteriormente pode anteceder esse marco.
- Juros simples: percentual não presumido; contagem explícita em meses inteiros ou pro rata die da rotina existente (dias / 30,4368, meses com seis casas). Base nos honorários corrigidos finais. HALF_UP ao centavo em contexto local, também na memória da taxa acumulada.
- Resultado inclui `atualizacao_valor_certo`, com componentes e memórias independentes. Fontes, entrada e hashes oficiais preservados. Total é valor fixado mais correção mais juros; custas IPCA-E somadas apenas depois, sem incidência de juros sobre elas.
- Validar fixação, início dos juros, incompatibilidades entre regime manual/oficial, série publicada e ausência de datas. Fixação ou juros na própria data-base não geram encargo por período não decorrido.
- Padrão da tela agora é atualizar desde a fixação. Alternar situação e regime conserva dados mas invalida resultado; payload remove taxas e datas ocultas. `Valor já na data-base` evita nova incidência, mantendo entradas antigas sem configuração de encargos.
- Cobertura considera somente correção escolhida, Taxa Legal quando aplicada e IPCA-E das custas. Dívidas ocultas não limitam as datas. API de cobertura acrescenta metadados da série oficial de juros.

## Interface e relatório

Reutilizadas grades, controles, cores e espaçamentos existentes; nenhum CSS, token, borda ou breakpoint novo. Campos seguem as grades compartilhadas em largura ampla e móvel. Identificação permanece primeiro bloco.

Resumo PDF em uma linha: valor fixado + correção + juros = honorários atualizados. Componentes em colunas próprias: encargo, início, fim, base com quatro casas, fator, taxa acumulada com seis casas e valor. Correção e juros têm memórias próprias com um cabeçalho por tabela. Metodologia e fontes encerram a memória, evitando uma página quase vazia somente de metodologia. Custas seguem em página exclusiva. Mantidos logo, paleta, Helvetica, margens, A4 horizontal e rodapé institucional.

## Conferência

- 193 testes de backend aprovados nos arquivos de valor certo, honorários isolados/principais/Fazenda/proveito econômico, IPCA + Taxa Legal e PDF. Incluem regressões do motor oficial e das exportações, períodos independentes, quantia sem período decorrido, validação de datas e taxas, custas fora da base, memória e cabeçalhos únicos.
- 46 testes da interface aprovados. Verificam três bases, campos dos regimes, exigência de datas, percentual condicional, payload limpo, preservação dos campos, limites por índice e detalhamento de resultado. Lint sem alertas, build concluído.
- API local final conferida: Taxa Legal e juros simples responderam HTTP 200 em JSON/PDF, ambos com quatro páginas no exemplo atualizado. Honorários no regime simples de 1% e contagem proporcional: R$ 1.636,18, apenas demonstrativos. Valor da causa, valor certo já na data-base e redução de dívida por faixas mantiveram HTTP 200 e respectivos PDFs. Preview e pacotes do build responderam HTTP 200; JavaScript final `index-l8SFcsYR.js`, CSS institucional inalterado.
- Exemplo hipotético: R$ 1.500,05 fixados em 15/01/2026, IPCA até 31/08/2026, juros pela Taxa Legal desde 03/03/2026. Correção R$ 44,29, juros R$ 52,31, honorários R$ 1.596,65; custas R$ 257,50, total R$ 1.854,15. Sem referência a autos reais ou comprovação de trânsito.
- PDF final com quatro páginas, todas renderizadas e inspecionadas; resumo, componentes, custas exclusivas, correção, juros, metodologia e fontes legíveis, sem sobreposição ou cortes. A versão inicial de cinco páginas foi reorganizada; nenhum PDF anterior de processo foi sobrescrito.
- Revisão interativa da tela, ampla/móvel, pendente: duas tentativas do navegador falharam (`trusted Node process exited unexpectedly` e `helper_unknown_error: apply deny-read ACLs`). Não foram alteradas permissões, segurança ou isolamento. Testes de renderização não equivalem à inspeção visual da tela.

Entrada: `backend/examples/honorarios_equidade_atualizada.json`. Saída: `output/pdf/exemplo_honorarios_valor_certo_atualizado.pdf`. PNGs finais: `tmp/pdfs/valor_certo_atualizado_qa/final/`.
