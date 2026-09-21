# Cálculos Jurídicos 1.10

Recuperação de cálculos e nova identidade visual do aplicativo.

- Cada novo cálculo recebe uma chave `CJ1-...`, exibida na tela e impressa no relatório PDF.
- O painel `Recuperar cálculo` reabre os dados completos para edição nos cálculos principais e de honorários.
- Os cálculos ficam armazenados somente neste computador e protegidos pela conta do Windows, sem importação retroativa de cálculos antigos.
- A nova logo passa a identificar a interface, o executável e o instalador, preservando a identidade Barreto Fontes nos relatórios PDF.
- A API local recebeu proteção adicional, e a integração com o Codex passa a registrar os cálculos com a mesma chave recuperável.
- A chave de assinatura das atualizações foi renovada; instalações da versão 1.09 ou anterior precisam instalar manualmente a 1.10 uma única vez.

# Cálculos Jurídicos 1.09

Integração direta com o Codex, sem abrir a interface do programa.

- O instalador agora registra um plugin pessoal do Cálculos Jurídicos no Codex.
- O Codex pode consultar critérios e executar os cálculos de débito, honorários por proveito econômico e honorários isolados pelo motor instalado.
- Os três fluxos podem gerar o mesmo relatório PDF usado na interface, devolvendo caminho, link local, tamanho e hash do arquivo.
- O conector funciona pelo protocolo MCP local e não depende do projeto-base nem de controle visual da tela.
- A integração acompanha as atualizações do programa, preserva outros plugins e é removida com segurança na desinstalação.

# Cálculos Jurídicos 1.08

Cobertura de índices corrigida e explicada conforme cada critério.

- Fazenda Pública 2 passa a usar a SELIC mensal oficial até agosto de 2026 e aceita data-base até 31/08/2026.
- Os avisos agora distinguem a data-base máxima do último dia ou competência efetivamente utilizados.
- Civil 1 e Civil 2 mostram corretamente que a data-base de 01/09/2026 é excluída e que os índices são usados até 31/08/2026.
- Combinações de honorários, custas e descontos informam qual parte do cálculo definiu o limite de data.
- Os relatórios PDF usam a mesma explicação, sem a mensagem genérica de “índices disponíveis até”.

# Cálculos Jurídicos 1.07

Fechamento integral do último mês publicado nos critérios civis.

- Civil 1 e Civil 2 agora aceitam o primeiro dia do mês seguinte como data-base máxima quando o IPCA do mês anterior já está publicado.
- Com o IPCA de agosto de 2026 disponível, a data-base máxima desses dois critérios passa a ser 01/09/2026.
- Como a data-base é excluída nos critérios civis, essa alteração garante a inclusão de todos os dias de agosto, inclusive 31/08.
- Valores negativos de IPCA continuam preservados e reduzem a correção monetária normalmente.

# Cálculos Jurídicos 1.06

Atualização acessível diretamente pelo programa.

- O rodapé passa a manter o botão `Verificar atualização` visível mesmo quando a versão instalada já é a mais recente.
- Quando houver uma edição nova no GitHub, o mesmo controle muda para `Atualizar para <versão>` e inicia o fluxo de download e instalação.
- Falhas de conexão exibem `Tentar novamente`, em vez de ocultar silenciosamente a ação.
- A área de atualização permanece visível também quando a janela está estreita.

# Cálculos Jurídicos 1.05

Identificação neutra e correta do IPCA-E.

- Removida das tabelas, critérios, metodologia e relatórios a referência legada à “convenção da CDA”.
- Os registros agora identificam claramente `IPCA-E anual (IBGE)` até 30/09/2022 e `IPCA-E mensal (IBGE)` a partir de 01/10/2022.
- A alteração é somente descritiva: os percentuais oficiais, períodos, truncamento e valores calculados permanecem inalterados.

# Cálculos Jurídicos 1.04

Correção do salvamento de relatórios no programa instalado.

- O botão `Baixar relatório PDF` agora abre o diálogo nativo do Windows para escolher onde salvar o arquivo.
- A mesma correção vale para os demais downloads gerados dentro do aplicativo, como PDF, Excel, CSV, memória em texto e modelo de importação.
- O arquivo temporário do navegador interno permanece disponível até o Windows iniciar efetivamente o salvamento.

# Cálculos Jurídicos 1.03

Extinção integral da dívida correta.

- Na apuração de honorários por redução de dívida, a opção `Dívida integralmente extinta` registra saldo remanescente de R$ 0,00 sem exigir parcela, data ou valor fictício.
- Itens já preenchidos ficam preservados na tela se a opção for desmarcada, mas não são enviados nem considerados enquanto a extinção estiver ativa.
- Resultado, memória e PDF documentam a extinção integral sem aplicar índices, juros ou multa à dívida correta.
- A dívida originalmente exigida continua exigindo ao menos um item positivo; a extinção integral só se aplica à dívida correta.

# Cálculos Jurídicos 1.02

Novos critérios da Fazenda Pública e civis.

- A lista principal passa a oferecer Fazenda Pública 1, 2, 3 e 4, com as transições específicas de IPCA-E, poupança, SELIC e juros de 2% ao ano.
- O antigo perfil IPCA-E + poupança passa a se chamar Fazenda Pública 3, sem perder a compatibilidade dos cálculos salvos.
- O antigo perfil de 2% passa a se chamar Fazenda Pública 4 e agora também aplica IPCA-E e poupança até 08/12/2021.
- IPCA + Taxa Legal passa a se chamar Civil 1.
- O novo Civil 2 aplica IPCA e juros de mora simples de 1% ao mês, com datas independentes.
- A série oficial da poupança foi completada de 09/12/2021 em diante para suportar a Fazenda Pública 1 sem lacunas.
- SELIC continua disponível como critério próprio.
- O instalador mantém a verificação automática de atualizações pelo GitHub e a validação de assinatura e integridade.
