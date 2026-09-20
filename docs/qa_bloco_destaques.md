# Destaques em bloco próprio

Ajuste solicitado em 17/09/2026 na tela Principal e honorários: o destaque contratual deixa de ficar dentro do cumprimento de sentença. A ordem passa a ser Honorários sucumbenciais, Cumprimento de sentença, Destaques e Custas e despesas processuais.

Extraído o componente DestaquesForm, reutilizando a mesma configuração e o callback SET_CUMPRIMENTO. Nenhuma alteração na API, no motor ou nas exportações. Percentual, base, exclusão de custas, ausência de acréscimo à dívida e invalidação do resultado permanecem iguais. Alterar a inclusão do destaque preserva as opções da multa/honorários do art. 523 e os valores anteriores do destaque.

A seção usa sheet-panel e section-heading, título próprio e identificação Divisão do crédito. Mantidos o filete amarelo, a superfície plana sem bordas, a tipografia compacta e o token comum de 64 pixels entre blocos. Percentual e base continuam na grade fees-contract-grid, que já passa para uma coluna até 700 pixels. Não há CSS, token, cor ou breakpoint novo. A margem interna antiga de contractual-options não é utilizada no novo bloco.

Cobertura: ordem dos blocos; ausência dos controles contratuais dentro do cumprimento; estado desativado; ambas as bases de destaque; campos ativos nas quatro combinações de multa e honorários do art. 523; alternância de inclusão sem perda de valores ou mutação da configuração original. Verificação visual ampla e móvel será tentada sem recarregar a aba do usuário.

## Validação concluída

33 testes de interface aprovados, incluindo três cenários novos de separação, independência dos acréscimos e preservação da configuração. Lint, tipos e build aprovados. CSS permanece index-Cw4F0pyM.css; o código atualizado é index-BVycfbzH.js, confirmado por HTTP na porta 4173 com o título/identificação do novo bloco e sem o rótulo antigo Acréscimos e destaque. Nenhum serviço do backend precisou ser reiniciado.

Conferência visual do navegador tentada após reset da sessão; a inicialização ainda termina com windows sandbox failed: helper_unknown_error: apply deny-read ACLs. Não alteradas configurações de segurança. Inspeção visual ampla e móvel permanece pendente; a renderização estática não é apresentada como inspeção visual. A aba do usuário não foi editada ou recarregada, preservando os dados da sessão. Exportar dados antes de recarregar para visualizar o novo build.

Diretriz permanente registrada nos itens 14 e 17 da interface em AGENTS.md. Motor, API, PDFs, CSV, Excel, entradas e resultados de processos reais não foram alterados nesta solicitação.
