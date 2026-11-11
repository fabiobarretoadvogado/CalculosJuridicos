# Atualização independente dos índices oficiais

Por escolha expressa de 06/10/2026, o aplicativo usa somente as novas bases oficiais canônicas e pacotes schema 2. A publicação de dados é separada do instalador e contém um ZIP e o manifesto `indices-update.json`. Inclui o conjunto coerente de bases e fontes, sem código, instalador, cálculos, chave privada ou credenciais.

## Uso no aplicativo

A seção Índices mostra fontes oficiais, primeiro e último registro, consulta e limites efetivos de cada perfil. INPC e IGP-M estão em JSON canônico; os cinco CSVs anteriores foram retirados da distribuição. Competências parciais da SELIC continuam sujeitas aos bloqueios próprios dos motores.

Um pacote local antigo é ignorado com aviso claro: as novas bases oficiais incorporadas são utilizadas, e os arquivos anteriores e os cálculos salvos são preservados. Não há conversão ou cópia derivada. A leitura não altera `active.json`, bancos, chaves, cálculos ou PDFs.

A ação Verificar e atualizar índices procura somente publicações `indices-v2-<revisão>`. Pacotes antigos não são oferecidos nem instalados. As versões anteriores do programa ignoram esse canal. O aplicativo com o novo leitor deve ser publicado antes do pacote formato 2; esta tarefa local não publicou nem instalou uma edição.

## Conferir e atualizar as séries

No diretório `liquidacao-custom`, o comando abaixo consulta INPC SGS 188 e IGP-M SGS 189 diretamente no Banco Central, sem gravar:

```powershell
backend/.venv/Scripts/python.exe -X utf8 scripts/atualizar_indices_mensais.py --verificar
```

Remover `--verificar` para atualizar somente os dois JSONs canônicos. `--serie inpc` ou `--serie igpm` restringe a consulta; `--consulta AAAA-MM-DD` informa uma data não futura nem anterior à consulta já registrada. Continuidade e cobertura são conferidas antes da gravação atômica de cada série. Variações negativas são preservadas. O script não recria CSVs, não projeta taxas e não publica.

O snapshot de IPCA-E, SELIC e poupança permanece gerado por `backend/data/fontes/gerar_snapshot.py`. As outras bases oficiais conservam seus processos existentes. Renovar datas somente quando as respectivas séries tiverem sido efetivamente consultadas.

## Preparar o pacote para revisão

```powershell
.\publicar-indices.ps1 -Preparar
```

A preparação usa exclusivamente os arquivos locais de `backend/data`, valida sequências, taxas, hashes, fontes e cobertura, gera o ZIP formato 2 e assina o manifesto. O ZIP é extraído em área temporária e validado novamente. Não compila o programa nem acessa o GitHub.

O resultado fica em `build/indices/indices-v2-<revisão>`. A lista permitida de 23 arquivos está em `index_data.store.FILES`. Scripts, arquivos adicionais, repetições, criptografia, links simbólicos e caminhos fora da lista são rejeitados. O leitor exige assinatura válida, schema 2, identidade do aplicativo, canal, revisão, endereço, tamanhos e hashes.

## Publicar somente os índices

Após autorização e revisão do pacote:

```powershell
.\publicar-indices.ps1 -Pacote 'build\indices\indices-v2-<revisão>'
```

O publicador cria uma release separada, com tag `indices-v2-<revisão>`, `prerelease=true` e `make_latest=false`. Envia somente ZIP e manifesto, compara os arquivos remotos e libera a publicação após confirmação. Não substitui publicações existentes. O comando `publicar.ps1` continua sendo o publicador do aplicativo completo.

## Armazenamento e auditabilidade

A base oficial incorporada acompanha o instalador. Pacotes oficiais formato 2 ficam em `indices/versions/<SHA-256>` no diretório dos cálculos; o override `CALCULOS_JURIDICOS_DATA_DIR` permanece isolado. A origem antiga permanece intacta para recuperação, mesmo quando ignorada pelo novo leitor.

Uma atualização formato 2 é conciliada com as fontes e não pode reduzir cobertura ou consulta em relação à base atual e à base incorporada. A ativação troca `active.json` atomicamente após a validação; o manifesto anterior e diretórios anteriores ficam arquivados. Cada operação fixa uma base única e registra hash, revisão, origem e `formato: 2`. Falhas de rede preservam a base anterior. Uma base local adulterada é rejeitada e a base incorporada fica em uso com aviso.

Cálculos antigos não são reescritos. Reabrir uma entrada para recalcular usa a nova base oficial atual; relatórios já emitidos são preservados. Exportação de um resultado cuja base mudou continua exigindo recálculo, evitando divergência entre tela e relatório. A importação de bancos de cálculos salvos não foi alterada.

Em 22/10/2026, por decisão expressa do usuário, o motor configurável antigo, seus módulos exclusivos de validação e abatimento, a regra antiga chamada `taxa_legal` em juros, a modalidade antiga de correção pelo mesmo nome e `backend/data/indices/taxa_legal.csv` foram removidos. O pacote assinado já excluía esse CSV. Civil 2 e Civil 3 preservam seus juros simples de 1% ao mês; os perfis de Taxa Legal oficial continuam usando a SGS 29543. A API atual recebe apenas o modelo de cálculo por perfis.

## Tarefa quinzenal

A tarefa existente mantém intervalo, modelo, execução e política de notificações. Seu trabalho de atualização deve conferir os JSONs canônicos e somente preparar o canal v2 depois da publicação do aplicativo com o novo leitor. Não publicar automaticamente. A definição armazenada da automação não foi alterada nesta tarefa.

## Verificação local

A validação desta alteração é pontual: bases oficiais, assinatura/lista fechada, rejeição de formato antigo sem alteração do ponteiro ou dos arquivos, atualização atômica formato 2, adulteração, regressão de cobertura, deflação, Civil 3 e limites independentes Civil 1. Não foi executada a suíte completa nem exame visual nesta migração. Evidências e limitações reais ficam em `migracao_bases_canonicas_20261006.md`.
