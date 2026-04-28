# Spec: Agent Runtime

## Overview

Implementar um runtime de coding agents no estilo Multica para o poly-bot. Cada mercado promissor vira uma task isolada executada por um agent configurável (Claude Code, OpenClaw, Hermes, OpenCode). O agent pesquisa dados reais via tools, calcula probabilidade e reporta resultado — tudo rastreável via dashboard.

## Functional Requirements

### FR-1: Task Dispatch
- O scanner deve criar uma Task para cada mercado promissor
- A task deve conter: market_id, question, timestamp, agent_config
- A task deve ser despachada para o runtime dentro de <2s

### FR-2: Agent Runtime Backend
- Interface unificada `AgentBackend` com método `execute(ctx, prompt, opts) -> Session`
- Auto-detecção de todos os CLIs disponíveis no PATH (até 10 runtimes):
  - `claude`, `codex`, `openclaw`, `opencode`, `hermes`, `gemini`, `pi`, `cursor-agent`, `kimi`, `kiro-cli`
- Cada runtime spawna seu CLI com parser específico de stdout
- Suporte a timeout configurável (default: 20min)
- Suporte a max_retries (default: 1, tenta próximo runtime disponível)
- Suporte a resume de sessão via `resume_session_id`
- Env var overrides para paths customizados (padrão Multica: `MULTICA_CLAUDE_PATH`, etc.)

### FR-2.5: Runtime Manager & Auto-Detection
- `RuntimeManager` singleton no processo principal
- `detect_installed_runtimes()`: verifica `shutil.which()` para cada CLI; cache em `~/.polybot/runtimes.json`
- `get_backend_for_runtime(name) -> AgentBackend`: factory via `BackendRegistry`
- `execute_task(task) -> Session`: orquestra workdir + backend + tracker
- Fallback ordenado: se o agent preferido não está instalado, tenta o próximo disponível na lista do agent

### FR-2.6: Task Lifecycle (Multica-style)
- Ciclo completo: `enqueue → claim → start → running → complete/fail`
- `enqueue`: task criada, `execution_log` status=`queued`
- `claim`: RuntimeManager marca task como `claimed` por um backend específico; previne race conditions
- `start`: backend spawna CLI, `execution_log` status=`running`
- `complete/fail`: resultado parseado, `execution_log` atualizado
- Retry: se um runtime falhar, RuntimeManager tenta o próximo runtime disponível (respeita `max_retries`)

### FR-3: Isolated Execution Environment
- Cada task cria um diretório isolado: `~/polybot_workspaces/{workspace_id}/{task_id}/`
- Estrutura do workdir:
  - `workdir/` — cwd do agent
  - `workdir/AGENTS.md` — instruções do agent (do DB)
  - `workdir/SOUL.md` — persona/voz (do DB)
  - `workdir/COMMANDS.md` — comandos customizados (do DB)
  - `workdir/.skills/*.md` — skills injetadas
  - `output/` — artefatos gerados pelo agent
  - `logs/` — logs da execução

### FR-4: Prompt Builder
- Construir prompt inicial baseado no tipo de mercado
- Incluir: question, yes/no prices, volume, resolution date
- Instruir agent a: research → gather data → calculate probability → responder em JSON
- JSON de resposta: `{"probability": float, "confidence": float, "reasoning": str, "sources": list[str]}`

### FR-5: Execution Tracking
- Tabela `execution_logs` com status pipeline (`queued → claimed → running → completed | failed | cancelled`)
- Tabela `execution_steps` com tracking granular (text | thinking | tool_use | tool_result | error | status)
- `ExecutionTracker` consome stream de mensagens e persiste em tempo real
- Cada mensagem do agent vira um step sequencial (seq INT)
- Dashboard acessa steps via polling HTTP `GET /api/executions/:id/steps` (5s interval)

### FR-6: Agent Registry
- CRUD de agents no banco (tabela `agents`)
- Seleção de agent por mercado: triggers configuráveis ou agent default
- Se múltiplos agents batem → rodar em paralelo e agregar (ensemble)
- Limite de concorrência por agent (`max_concurrent_tasks`)

### FR-7: Skills Management
- CRUD de skills no banco (tabela `skills`)
- Skills são markdown injetado no contexto do agent
- Tabela de junção `agent_skills` (many-to-many)
- Injeção de skills como arquivos `.md` no workdir

### FR-8: Dashboard Integration
- API endpoints: `GET/POST/PUT/DELETE /api/agents`, `/api/skills`, `/api/executions`
- Páginas React: Agents, Skills, Executions
- Componentes: AgentCard, AgentForm, SkillEditor, ExecutionTimeline
- Hooks: useAgents, useSkills, useExecutions (TanStack Query)

### FR-9: Scanner Integration
- Refatorar `scanner.py` para usar `AgentRuntime` em vez de agents legados diretamente
- Decision gate usa `probability` e `confidence` do resultado do agent
- Fallback automático para agents legados se runtime falhar
- Manter contagem de bets e lógica de deduplication existente

### FR-10: Fallback & Resilience
- Se runtime falhar (timeout, agent_error, runtime_offline), usar agents legados
- Se nenhum agent retornar resultado, rejeitar mercado
- Circuit breaker para runtimes offline (3 falhas consecutivas = 5min cooldown)

## Non-Functional Requirements

### NFR-1: Performance
- Task dispatch latency: <2s do scanner para o agent iniciar
- Step tracking: persistência em <500ms por mensagem
- Dashboard API: <200ms para listagens

### NFR-2: Reliability
- Tasks completadas com sucesso: >90%
- Fallback para agents legados: 100% das vezes que o runtime falha
- DB schema idempotente (múltiplas inits seguras)

### NFR-3: Security
- Workdirs isolados por task
- Env vars de API keys não expostas no prompt
- Custom env por agent (não global)

### NFR-4: Observability
- 100% das execuções logam steps em `execution_steps`
- Token usage tracking (input/output/cache) quando o runtime reportar
- Error tracking com `failure_reason` categorizado

## Acceptance Criteria

### AC-1: End-to-End Execution
```gherkin
Given o scanner encontrou o mercado "Temperatura máxima em Seul > 25°C amanhã?"
And o AgentRegistry selecionou o WeatherBot (Claude Code)
When o scanner despacha a task para o runtime
Then o ClaudeBackend spawna o processo claude no workdir isolado
And o agent recebe o prompt com instruções de research
And o agent executa web_search e fetch_url
And o resultado {"probability": 0.12, "confidence": 0.85} é persistido em execution_logs
And os steps são visíveis em execution_steps
And o decision gate usa o resultado para aceitar/rejeitar a aposta
```

### AC-2: Dashboard CRUD
```gherkin
Given o operador acessa o dashboard
When navega para a aba "Agents"
Then vê lista de agents cadastrados
When clica em "+ New Agent"
Then preenche nome, runtime, model, system prompt, skills
And o agent é salvo no banco
And aparece na lista
```

### AC-3: Fallback
```gherkin
Given o runtime Claude Code está offline
When o scanner despacha uma task
Then o ExecutionTracker marca como failed com failure_reason="runtime_offline"
And o scanner fallback para agents legados (sports_analyst, etc.)
And a aposta continua sendo avaliada
```

### AC-4: Skills Injection
```gherkin
Given o WeatherBot tem a skill "weather_research" vinculada
When uma task é despachada para o WeatherBot
Then o workdir contém `.skills/weather_research.md`
And o prompt inicial menciona que skills estão disponíveis em `.skills/`
```

## Out of Scope
- Blockchain execution (live trading continua como tag-only)
- Autoscaling / multi-instance
- Billing / cost tracking por agent
- WebSocket / Server-Sent Events para streaming real-time (MVP usa polling HTTP)
- ACP/JSON-RPC implementations for Hermes/OpenClaw/Kiro (Phase 1 implements only CLI stdout parsers)
- Multi-workspace / multi-tenant (bot é single-operator)
