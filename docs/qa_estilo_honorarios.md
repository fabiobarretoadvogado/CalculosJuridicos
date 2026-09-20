# Honorários sucumbenciais no padrão visual das custas

Ajuste solicitado e implementado em 17/09/2026, na tela Principal e honorários.

Quando não incluídos, os honorários usam o mesmo aviso compacto das custas: fundo institucional claro, ícone de 20 pixels, altura mínima de 52 pixels e texto de 11 pixels, pela classe existente `costs-empty`. Abaixo aparece `Adicionar honorários sucumbenciais`, usando o mesmo botão ghost sem bordas e espaçamento `cost-add` das custas. O checkbox anterior foi retirado somente desse bloco.

Quando incluídos, aparecem os campos aplicáveis à base e a ação `Remover honorários sucumbenciais`. Adicionar, remover ou reincluir altera apenas `aplicar`, preservando base, percentual, índice, data e valores. Reutilizado o callback existente; a ação SET_HONORARIOS continua invalidando o resultado anterior. Botões são do tipo button e não submetem o cálculo; estado de expansão é identificado por ARIA.

Não alterados CSS, tokens, fontes compartilhadas, cores, bordas ou breakpoints. As dimensões móveis acompanham os estilos atuais das custas e dos campos. Não alterados seletores do cumprimento de sentença, categoria autônoma de honorários, backend, cálculos ou PDFs.

## Validação

30 testes de interface aprovados, incluindo três verificações novas: aviso/ação no estado vazio, campos/remoção no estado ativo e sequência adicionar-remover-reincluir preservando todos os valores. O teste anterior de estados vazios foi atualizado para abranger os quatro avisos agora existentes. Compilação, verificação de tipos e lint aprovados. CSS do build permanece `index-Cw4F0pyM.css`; o novo código está em `index-BWcmvkaQ.js`.

Acesso ao navegador tentado, com reset e uma repetição; a inicialização falhou com `windows sandbox failed: helper_unknown_error: apply deny-read ACLs`. Não alteradas permissões ou configurações de segurança. Conferência visual do navegador em largura ampla e móvel continua pendente; testes de renderização não são apresentados como inspeção visual. A aba do usuário não foi recarregada nem editada.

Regra permanente registrada no item 16 das Diretrizes Visuais Permanentes da Interface, em AGENTS.md. O preview existente deve exibir a alteração ao recarregar; dados não exportados devem ser preservados antes, pois o aplicativo mantém entradas somente na sessão da página.
