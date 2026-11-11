# Suíte de testes

Execute os comandos na raiz de `liquidacao-custom`, com as dependências de desenvolvimento do backend instaladas em `backend/.venv` e as do frontend em `frontend/node_modules`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-suite.ps1 -Listar
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-suite.ps1 -Suite rapida
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-suite.ps1 -Suite completa
```

| Suíte | Abrangência | Quando usar |
| --- | --- | --- |
| `rapida` | Regressões essenciais do motor, limites dos índices, fontes oficiais e todos os testes do frontend | Durante o desenvolvimento |
| `motor` | Cálculos por perfil, parcelas, descontos, honorários, juros e exportações relacionadas | Ao mudar fórmulas ou entradas |
| `integracao` | API, persistência, importação, desktop, MCP, Codex e atualizações | Ao mudar contratos ou serviços |
| `relatorios` | PDF, paginação, anexos e apresentação das rubricas | Ao mudar relatórios |
| `indices` | Fontes oficiais, catálogo, integridade, pacote assinado e caminho da chave | Ao mudar dados ou publicação de índices |
| `frontend` | Todos os arquivos de teste reconhecidos pelo executor Node | Ao mudar a interface |
| `completa` | Todos os testes descobertos pelo pytest e pelo Node, mesmo se uma das etapas falhar | Antes de uma entrega |

Os grupos do backend são organizados por **arquivo**. Alguns arquivos do motor também testam API, PDF e Excel de ponta a ponta. Cada arquivo pertence a um único grupo; o executor acusa arquivos novos sem grupo, arquivos ausentes e duplicações. A suíte `completa` sempre aponta para o diretório inteiro de testes do backend, de modo que nenhum teste é omitido por essa classificação. O comando `npm test` usa a descoberta automática do Node para incluir novos arquivos de teste do frontend.

Para conferir a coleta sem executar os testes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-suite.ps1 -Suite completa -Coletar
```

Cada execução do backend usa um diretório novo em `build/test-suite/` para os temporários do pytest. A fixture de `backend/tests/conftest.py` direciona os dados locais de cada teste para esse temporário, sem usar o cadastro real do aplicativo. O executor informa o caminho ao final e retorna código diferente de zero quando uma etapa falha. Em caso de falha na suíte completa, ele ainda executa os testes do frontend e mostra o resultado de ambas as etapas.

Os testes de API usam `TestClient`, que precisa criar sockets locais para o loop de eventos. Um ambiente que bloqueie esses sockets pode deixar a execução parada; o pytest imprime as pilhas após 60 segundos para ajudar no diagnóstico. Isso é uma limitação do ambiente de execução, não resultado aprovado. Rode novamente em um terminal local com acesso a sockets e confira o resultado completo antes de liberar uma entrega.
