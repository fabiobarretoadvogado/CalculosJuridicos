# Referência mensal SELIC/CJF - 18/09/2026

Solicitação: apresentar a data-base SELIC como 01/08/2026 e identificar 07/2026 como última competência aplicada, sem sugerir atualização diária até 31/08.

## Regra e escopo

- Apenas o perfil `selic_cjf_v1`: soma mensal simples, com a taxa de uma competência computada no mês seguinte. A aritmética não foi alterada.
- `data_referencia_selic` identifica o primeiro dia do mês; `ultima_competencia_selic` identifica a última taxa efetivamente presente na memória. Quando não há memória, o último índice é nulo e aparece como nenhum, não como uma taxa inventada.
- Preservadas a entrada original e a cobertura `data_base_maxima` da API. Novos campos distinguem referência mensal máxima e última competência utilizável nessa cobertura.
- Custas, valor da causa e descontos com outro perfil continuam utilizando a data exata informada. Resultados mistos exibem separadamente a data final das demais operações.
- Identificação em resultado principal, critérios do formulário, cabeçalho/rodapés/fontes do PDF e dados gerais do Excel. JSON e premissas do CSV/Excel preservam as novas referências. As operações autônomas de honorários reutilizam os critérios do motor.
- Sem novo cartão, borda, cor, fonte, tamanho ou breakpoint. Reutilizados os estilos existentes e a quebra natural do texto.

## Caso 5061447-27.2025.4.04.7000

Entrada alterada para 01/08/2026 exclusivamente neste caso sem encargos diários. Taxas até 07/2026; 19 competências de março/2024 a setembro/2025. Conferência independente pelo SGS 4390, motor local, API e reconciliação do Projef nos autos.

Principal R$ 23.404,77; SELIC R$ 5.119,11; total provisório R$ 28.523,88. A execução em 01/08 e em 31/08 gera o mesmo resumo. As ressalvas jurídicas e a ausência de trânsito comprovado continuam expressas.

PDF atual: `output/pdf/relatorio_5061447-27.2025.4.04.7000_2026-08-01_provisorio.pdf`. Não houve sobrescrita do caminho de 31/08 nesta alteração, mas esse PDF anterior não foi localizado na conferência final; não se afirma sua preservação. Permanecem as imagens da inspeção anterior em `tmp/pdfs/caso_5061447_20260918`. Original dos autos preservado, com SHA-256 reconferido pela rotina deste caso.

## Validação

- Backend: 135 testes aprovados nos módulos SELIC/CJF, descontos, honorários principais, multas, honorários por redução de dívida e PDF. Inclui referência mensal, nenhum índice aplicado, 20 parcelas SELIC, data exata de custas/valor da causa, exportações, 36 parcelas com múltiplos componentes e texto extenso. Um aviso de descontinuação do Starlette, sem erro funcional.
- Frontend: 35 testes aprovados; build e verificação de consistência aprovados. Não se afirma aprovação da suíte integral de todos os outros módulos do projeto.
- API local reiniciada somente para este projeto; cálculo e PDF responderam com sucesso e coincidiram com o motor local.
- As três páginas do PDF final foram renderizadas em PNG e inspecionadas: logo, referência 01/08/2026, último índice 07/2026, valores, cabeçalho único, colunas constantes nas continuações, última parcela junto ao total, fontes e rodapés preservados. Sem corte ou sobreposição identificados.
- Não foi realizada inspeção visual interativa da tela; a apresentação foi validada pelos testes de renderização. Não houve mudança de estilos ou preenchimento da sessão do navegador.
