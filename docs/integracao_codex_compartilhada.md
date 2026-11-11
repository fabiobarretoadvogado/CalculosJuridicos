# Integração compartilhada com o Codex

A partir da edição 1.20, a opção de integração instala um único servidor HTTP
local para todos os chats. O instalador inclui um Python independente, compatível
com o arquivo de módulos do aplicativo, e não depende do ambiente do Codex.

O servidor carrega o motor e os recursos da distribuição instalada por uma cópia
privada, sem executar o ponto de entrada gráfico. Assim, a conexão não inicia
um executável completo por chat e evita a atividade nativa observada no modo
windowed/STDIO. O motor financeiro e os geradores não são reimplementados no conector.

## Instalação e atualização

- O serviço reside em .codex/integrations/calculos-juridicos no perfil do usuário,
  fora dos diretórios sujeitos à virtualização de AppData.
- A tarefa CalculosJuridicosMCP inicia no login, sem janela e sem elevação.
- A trava de arquivo e a política IgnoreNew impedem instâncias duplicadas.
- A conexão escuta somente em 127.0.0.1, com uma chave aleatória por usuário.
- A chave e a porta são preservadas durante atualizações e reinstalações.
- O plugin permanece habilitado. Seu servidor STDIO antigo fica desabilitado;
  o servidor HTTP é registrado nas configurações compartilhadas do Codex.
- O instalador encerra apenas o serviço e conectores legados --mcp antes de
  substituir arquivos. Janelas normais continuam protegidas pelo instalador.
- Após copiar a versão nova, o instalador prepara, inicia e verifica o serviço.
  Uma falha na verificação não é tratada como integração bem-sucedida.
- Desmarcar a integração remove o registro anterior. A desinstalação remove a
  tarefa e somente as configurações reconhecidas como gerenciadas pelo aplicativo.

Na primeira migração de STDIO para HTTP, reinicie o Codex para descarregar as
conexões antigas dos chats abertos. Atualizações posteriores mantêm o endereço
e a chave. O serviço usa uma cópia dos recursos para não bloquear o atualizador;
se detectar a substituição do executável, encerra e a tarefa o reinicia.

Os bancos e as chaves de recuperação continuam sob responsabilidade do
armazenamento canônico existente. Não são removidos pelo serviço. Backups de
configuração e registros de diagnóstico são preservados na pasta do serviço.

## Verificação de distribuição

O build.ps1 prepara codex-service/ e executa scripts/smoke_shared_mcp.py.
O teste usa dados e pasta temporários, oito clientes, autenticação, trava de
instância única, cálculo, PDF e medição de CPU em repouso. Não instala tarefas
nem altera a integração real do perfil que compila o programa.

O instalador é gerado somente se o ambiente do serviço estiver presente.
O teste de protocolo STDIO é mantido para compatibilidade com o comando manual
--mcp, que deixou de ser o transporte padrão da integração.
