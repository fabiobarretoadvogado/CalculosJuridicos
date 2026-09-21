---
name: calculos-juridicos
description: Use quando o usuário pedir cálculo ou atualização de débito judicial, honorários sucumbenciais, memória de cálculo ou relatório PDF pelo aplicativo Cálculos Jurídicos instalado.
---

# Cálculos Jurídicos

Use exclusivamente as ferramentas MCP deste plugin para executar o motor do aplicativo. Não refaça a conta manualmente e não substitua as séries oficiais por conhecimento geral.

Antes do primeiro cálculo, consulte `informacoes_aplicativo` e `consultar_criterios` para confirmar o perfil e a cobertura disponível. Para honorários por valor da causa, consulte também `consultar_cobertura_honorarios`.

Peça ao usuário os dados jurídicos ou financeiros que faltarem. Nunca presuma data-base, vencimento, início dos juros, perfil, percentual, multa, valor pago, natureza da base ou extinção da dívida.

Use:

- `calcular_debito_judicial` para o cálculo principal;
- `calcular_honorarios_proveito_economico` para honorários sobre a redução de uma dívida;
- `calcular_honorarios_isolados` para valor da causa ou valor certo;
- a ferramenta `gerar_pdf_*` correspondente quando o usuário quiser um relatório.

Prefira `modo_resultado="resumo"` na conversa. Use `modo_resultado="completo"` apenas quando o usuário pedir memória detalhada ou auditoria. Depois de gerar um PDF, entregue o link de recurso e informe o caminho absoluto retornado pela ferramenta.

Explique que os resultados dependem das entradas informadas e dos índices incluídos na versão instalada. Preserve os alertas e as premissas do motor; não os reinterprete como parecer jurídico.
