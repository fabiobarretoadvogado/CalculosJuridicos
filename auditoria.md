# 🔍 Auditoria Completa — Projeto "Liquidação Judicial Custom"

**Data:** 2026-07-07
**Testes:** 32 passaram ✅ | 3 erros (erro de permissão do Windows no `tmp_path`, não é bug do projeto)

---

## 🔴 CRÍTICOS (corrigir imediatamente — 5 bugs)

| # | Arquivo | Problema |
|---|---------|----------|
| **1** | `backend/liquidacao_custom/core/parcelas.py:100` | **`NameError`**: `date.max` usado mas `date` não foi importado. Se qualquer parcela não tiver `data_vencimento`, o sistema quebra em runtime. **Correção:** Adicionar `from datetime import date`. |
| **2** | `backend/liquidacao_custom/core/indices.py:85-98` | **Correção zero no mesmo mês**: `calcular_fator_acumulado` usa `while <` (exclusivo) em vez de `<=`. Períodos dentro do mesmo mês recebem fator `1.0` (zero correção). **Correção:** Alterar para `<=`. |
| **3** | `backend/liquidacao_custom/core/motor.py:89-107` | **Duplicação de SELIC**: Transição taxa legal → SELIC pode criar períodos de correção duplicados, aplicando correção em dobro. **Correção:** Verificar se já existe período SELIC antes de adicionar. |
| **4** | `backend/liquidacao_custom/core/abatimentos.py:200-218` | **Perda de centavos**: Arredondamento individual de cada parcela no abatimento proporcional faz a soma não bater com o valor original. **Correção:** Aplicar arredondamento só na última parcela (resto). |
| **5** | `backend/liquidacao_custom/core/preenchimento_serie.py:28-48` | **Dia fixo em 28**: Após Fevereiro, `min(data_atual.day, 28)` fixa permanentemente o dia 28 para todos os meses seguintes (Março 28, Abril 28...). **Correção:** Usar `calendar.monthrange(ano, mes)[1]` por mês. |

---

## 🟠 ALTOS (corrigir no curto prazo — 10 problemas)

### Backend

| # | Arquivo | Problema |
|---|---------|----------|
| **6** | `backend/liquidacao_custom/core/abatimentos.py:240-249` | **`valor_corrigido` negativo**: Subtração no abatimento pode tornar `valor_corrigido` negativo, quebrando a consistência `total = corrigido + juros + multa`. Usar `min(restante, p.valor_corrigido)`. |
| **7** | `backend/liquidacao_custom/core/indices.py:42-52` | **CSV malformado quebra tudo**: `KeyError`/`DecimalException` não tratados. Uma linha corrompida no CSV derruba o cálculo inteiro. Envolver em `try/except`. |
| **8** | `backend/liquidacao_custom/core/juros.py:83-86` | **Perda de precisão em juros compostos**: Usa `ln()`/`exp()` em vez de `**` para exponenciação, acumulando erro em períodos longos. |
| **9** | `backend/liquidacao_custom/core/preenchimento_serie.py:126` | **Salário mínimo desatualizado**: Hardcoded R$ 1.212 (2022). Em 2026, o valor real é ~R$ 1.518. Atualizar ou obter do CSV. |
| **10** | `backend/liquidacao_custom/core/importador_excel.py:164-186` | **Falha silenciosa ao parsear datas**: Se a data não encaixa em nenhum formato, o erro não é registrado em `linha_erros`. Adicionar `linha_erros.append(...)` no `except`. |

### API

| # | Arquivo | Problema |
|---|---------|----------|
| **11** | `backend/liquidacao_custom/api/main.py:19-25` | **CORS inválido**: `allow_origins=["*"]` com `allow_credentials=True` é rejeitado por navegadores. Remover credenciais ou usar origens explícitas. |
| **12** | `backend/liquidacao_custom/api/routes.py` (vários) | **`str(e)` vaza nas respostas HTTP**: Caminhos do servidor e dados internos expostos em mensagens de erro. Retornar mensagem genérica + log interno. |
| **13** | `backend/liquidacao_custom/api/routes.py` (vários) | **Vazamento de arquivos temporários**: Se `exportar_excel()` ou `exportar_csv()` falham, os `tempfile` nunca são removidos. Usar `try/finally`. |
| **14** | `backend/liquidacao_custom/api/routes.py:142-145` | **`UnboundLocalError`**: `tmp_path` referenciada no `except` antes de ser atribuída, mascarando a exceção original. Inicializar com `None`. |

### Frontend

| # | Arquivo | Problema |
|---|---------|----------|
| **15** | `frontend/src/contexts/CalculoContext.tsx:326` | **`base_calculo` da multa CPC523 ignorado**: O state do usuário é sobrescrito por `'subtotal_atualizado'` fixo no `buildCalculoJudicial`. Remover o override ou o campo do state. |

---

## 🟡 MÉDIOS (resolver no próximo ciclo — 16 problemas)

### Backend

| # | Arquivo | Problema |
|---|---------|----------|
| **16** | `backend/liquidacao_custom/core/validacoes.py:122-137` | Código morto: validação 3 e 4 checam valores de enum já garantidos pelo Pydantic. Remover. |
| **17** | `backend/liquidacao_custom/core/acessorios.py:60-80` | CSV de salário mínimo lido a cada chamada sem cache. Usar `lru_cache` ou cache em módulo. |
| **18** | `backend/liquidacao_custom/core/acessorios.py:300-305` | Late imports dentro de função — provável dependência circular. Mover para o topo. |
| **19** | `backend/liquidacao_custom/core/acessorios.py:337-369` | Campo `correcao_monetaria` de Astreintes definido no modelo mas nunca aplicado no cálculo. |
| **20** | `backend/liquidacao_custom/core/exportadores.py:37` | `hasattr(m, 'fator_applied')` sempre `False` — atributo inexistente. Simplificar para `m.fator_aplicado`. |
| **21** | `backend/liquidacao_custom/core/validacoes.py:43` | Passa `CalculoJudicial` inteiro quando só precisa de um campo (`data_inicio_vigencia`). |
| **22** | `backend/liquidacao_custom/core/validacoes.py:74-87` | Dupla iteração sobre `calculo.parcelas`. Mover lógica para dentro de `_validar_parcela`. |
| **23** | `backend/liquidacao_custom/core/correcao.py:53-61` | `INDICE_MANUAL` recalcula `valor_base` por divisão reversa — frágil. Usar padrão `valor_antes = valor_corrigido`. |
| **24** | `backend/liquidacao_custom/core/acessorios.py` (todo) | Mojibake nos comentários — corrupção de encoding UTF-8. |
| **25** | `backend/liquidacao_custom/core/models.py` (vários) | Campos numéricos sem `Field(ge=0)`, strings sem `max_length`. |
| **26** | `backend/liquidacao_custom/core/models.py:131-152` | Sem `@model_validator` para garantir `data_inicial <= data_final`. |

### Frontend

| # | Arquivo | Problema |
|---|---------|----------|
| **27** | `frontend/src/pages/Processamento.tsx:955` | Bloco de "Abatimentos" com condição `length < 0` (sempre `false`) — código morto. |
| **28** | `frontend/src/pages/Exportacao.tsx:75-131` | Texto do relatório com encoding corrompido (caracteres ilegíveis como `Ã‡ÃƒO`). |
| **29** | `frontend/src/components/ui/Modal.tsx` | Sem `role="dialog"`, `aria-modal`, focus trap, ou tecla Escape. |
| **30** | `frontend/src/pages/Processamento.tsx:382-389` | Campo "Juízo" destrutivo: editar sobrescreve `vara` e apaga `comarca`. |
| **31** | `frontend/src/services/api.ts:3` | `API_BASE_URL` hardcoded como HTTP (sem HTTPS, sem variável de ambiente). |

---

## 🟢 BAIXOS (melhorias contínuas — 9 problemas)

| # | Arquivo | Problema |
|---|---------|----------|
| **32** | `backend/liquidacao_custom/api/routes.py:113` | `async def` com I/O síncrono bloqueante — anula benefício do async. |
| **33** | `backend/liquidacao_custom/api/routes.py` (todos) | Zero autenticação em todos os endpoints. |
| **34** | `backend/liquidacao_custom/api/routes.py` (todos) | Sem rate limiting — endpoints de cálculo suscetíveis a DoS. |
| **35** | `backend/liquidacao_custom/api/routes.py:154-162` | `os.listdir()` em cada GET `/indices` sem cache. |
| **36** | `backend/liquidacao_custom/api/routes.py:59-100` | Geração de Excel/CSV passa pelo disco — `BytesIO` seria mais eficiente. |
| **37** | `frontend/src/components/ui/FileUpload.tsx:22-28` | Drag-and-drop não valida extensão (aceita qualquer arquivo). |
| **38** | `frontend/src/pages/Importacao.tsx:84-91` | Arrays de opções recriados em todo render — faltou `useMemo`. |
| **39** | `backend/pyproject.toml:25` | Dependência `httpx2` não existe no PyPI — deveria ser `httpx`. |
| **40** | `backend/liquidacao_custom/api/routes.py` (todos) | Zero logging estruturado. |

---

## 📊 Resumo por categoria

| Categoria | Crítico | Alto | Médio | Baixo |
|-----------|---------|------|-------|-------|
| Bugs de lógica/cálculo | 5 | 5 | 5 | 0 |
| Validação/segurança | 0 | 4 | 4 | 4 |
| Performance | 0 | 0 | 3 | 3 |
| Código/UX | 0 | 1 | 5 | 2 |

**Total: 40 problemas encontrados** — 5 críticos, 10 altos, 16 médios, 9 baixos.

---

## 🎯 Arquivos mais problemáticos

| Arquivo | Ocorrências |
|---------|-------------|
| `backend/liquidacao_custom/api/routes.py` | 9 |
| `backend/liquidacao_custom/core/models.py` | 5 |
| `backend/liquidacao_custom/core/validacoes.py` | 3 |
| `frontend/src/pages/Processamento.tsx` | 3 |
| `backend/liquidacao_custom/core/acessorios.py` | 3 |

---

## ✅ Testes

**32/35 passaram.** Os 3 que falharam são por `PermissionError` no diretório temporário do pytest no Windows (`C:\Users\isabe\AppData\Local\Temp\pytest-of-isabe`) — não são bugs do código, mas um problema de permissão do ambiente.
