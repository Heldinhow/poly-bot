# Tasks: Token Optimization & Execution Visibility

## Tarefas (ordenadas por impacto)

### Task 1: Cache de Análise de Mercado [ALTO IMPACTO]
**Arquivo:** `db/cache_repository.py` (NOVO) + `db/schema.sql`

- [ ] Criar tabela `market_analysis_cache` no schema.sql
- [ ] Criar `CacheRepository` com métodos:
  - `get_cache(market_id)` → retorna última análise
  - `set_cache(market_id, question, yes_price, no_price, probability, confidence, reasoning, agent_name, decision)`
  - `should_analyze(market_id, current_yes_price, threshold=0.05)` → bool
- [ ] Integrar cache no scanner.py antes de chamar AgentRunner

### Task 2: Filtros Estáticos Mais Rigorosos [ALTO IMPACTO]
**Arquivo:** `config.py` + `filters.py`

- [ ] Atualizar `config.py`:
  - `max_price: 0.25` (era 0.35)
  - `max_odds: 10.0` (era 20.0)
  - `min_volume: 20000` (era 10000)
  - `scan_interval_secs: 300` (era 60)
- [ ] Adicionar `min_odds: 2.0` em config.py
- [ ] Atualizar `filters.py` para usar min_odds

### Task 3: Substituir Claude Code por MiniMax API [ALTO IMPACTO]
**Arquivo:** `agents/runtime/runner.py` (REWRITE)

- [ ] Criar método `_analyze_with_minimax(question, yes_price, no_price, volume)`
- [ ] Usar httpx para chamar `https://api.minimax.chat/v1/text/chatcompletion_v2`
- [ ] Formatar prompt padrão com dados do mercado
- [ ] Parsear resposta JSON (probability, confidence, reasoning)
- [ ] Retornar Result com dados parseados
- [ ] Logar: prompt enviado, tokens usados, duração

### Task 4: Logging Detalhado [MÉDIO IMPACTO]
**Arquivo:** `agents/runtime/runner.py` + `db/execution_repository.py`

- [ ] Adicionar coluna `agent_name` em execution_logs
- [ ] Adicionar coluna `prompt_used` em execution_logs (TEXT)
- [ ] Atualizar `create_log()` para aceitar agent_name e prompt_used
- [ ] Logar no scanner:
  ```
  [AgentRunner] Analyzing: "Will WTI hit $110?"
    Agent: CommodityBot (MiniMax-M2.7)
    Prompt: "You are a probability estimator..."
    Result: probability=0.25, confidence=0.70
    Tokens: 1,234 in / 456 out
    Duration: 2.3s
  ```

### Task 5: Dashboard - Mostrar Detalhes da Execução [MÉDIO IMPACTO]
**Arquivo:** `frontend/src/pages/ExecutionsPage.tsx` + `api.py`

- [ ] Atualizar API `/api/executions` para retornar agent_name, prompt_used
- [ ] Atualizar frontend para mostrar:
  - Nome do agent
  - Prompt usado (colapsável)
  - Tokens usados
  - Duração
  - Probabilidade calculada

### Task 6: Atualizar AGENTS.md e Docs [BAIXO IMPACTO]
**Arquivo:** `AGENTS.md`, `docs/apis.md`, `docs/changelog.md`

- [ ] Documentar novos parâmetros de filtro
- [ ] Documentar cache de análise
- [ ] Documentar mudança de Claude Code para MiniMax API
- [ ] Atualizar changelog

## Ordem de Execução

1. Task 1 (Cache) — evita re-análises
2. Task 2 (Filtros) — reduz mercados analisados
3. Task 3 (MiniMax API) — reduz custo por análise
4. Task 4 (Logging) — visibilidade
5. Task 5 (Dashboard) — UX
6. Task 6 (Docs) — documentação

## Métricas de Validação

Após implementação, verificar:
- [ ] Tokens por análise <3,000 (era ~38,000)
- [ ] Análises por hora <3 (era ~10)
- [ ] Requests MiniMax/dia <200 (era ~735 em 5h)
- [ ] Cache hit rate >50% (mercados pulados)
- [ ] 100% das execuções com log completo
