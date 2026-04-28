# Tasks: Agent Runtime

## Ordering Principle

Tasks are ordered by **dependency chain** and **foundation-first**:
1. Database schema (foundation for everything)
2. Data access layer (repositories)
3. Runtime core models (dataclasses)
4. Backend implementations (depend on models)
5. Execution environment (depends on backend)
6. Prompt builder (depends on models)
7. Execution tracker (depends on DB + models)
8. Agent registry (depends on repositories)
9. Scanner integration (depends on runtime + registry + tracker)
10. Dashboard API (depends on repositories)
11. Dashboard frontend (depends on API)
12. Default skills (depends on skills system)
13. Polish & docs

---

## Task 1: Database Schema — Runtime Tables
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 2-3h  
**Dependencies**: None

### Description
Create new tables in PostgreSQL for agents, skills, execution tracking.

### Acceptance Criteria
- [ ] `agents` table created with all fields (UUID PK, name, runtime, model, system_prompt, skills[], max_concurrent_tasks, custom_args, custom_env, is_active, is_archived)
- [ ] `skills` table created (UUID PK, name, description, content, is_active)
- [ ] `agent_skills` junction table created
- [ ] `execution_logs` table created with status pipeline, timing, result, token usage
- [ ] `execution_steps` table created with tool_use/tool_result tracking
- [ ] All indexes created (market_id, status, agent_id, seq)
- [ ] Schema init is idempotent (safe to run multiple times)
- [ ] `updated_at` trigger for `agents` and `skills`

### Files to Modify
- `db/schema.sql` — add new tables and indexes
- `db/connection.py` — ensure schema init covers new tables

---

## Task 2: Repositories — Agent, Skill, Execution
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 4-5h  
**Dependencies**: Task 1

### Description
Implement repository pattern for the new tables.

### Acceptance Criteria
- [ ] `AgentRepository` with: create, get_by_id, get_by_name, list_active, update, delete, archive
- [ ] `SkillRepository` with: create, get_by_id, list_active, update, delete
- [ ] `ExecutionRepository` with: create_log, update_log, get_log, list_logs, create_step, list_steps
- [ ] `AgentSkillRepository` with: link, unlink, get_skills_for_agent, get_agents_for_skill
- [ ] All repositories use parameterized queries (no SQL injection)
- [ ] Repositories follow existing `BetRepository` patterns

### Files to Create
- `db/agent_repository.py`
- `db/skill_repository.py`
- `db/execution_repository.py`

### Files to Modify
- `db/__init__.py` — export new repositories

---

## Task 3: Runtime Models
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 2h  
**Dependencies**: None

### Description
Create dataclasses for the agent runtime domain.

### Acceptance Criteria
- [ ] `MessageType` enum with: TEXT, THINKING, TOOL_USE, TOOL_RESULT, STATUS, ERROR, LOG
- [ ] `Message` dataclass with type, content, metadata
- [ ] `Result` dataclass with probability, confidence, reasoning, sources, raw_output, error_message, token counts
- [ ] `ExecOptions` dataclass with cwd, model, system_prompt, timeout, max_retries, resume_session_id, custom_args, custom_env
- [ ] `ExecutionContext` dataclass with task_id, market_id, agent_id, workspace_id
- [ ] `Session` class with messages (AsyncIterator) and result (asyncio.Future)
- [ ] `AgentBackend` ABC with `execute()` method

### Files to Create
- `agents/runtime/models.py`
- `agents/runtime/__init__.py`

---

## Task 3b: Runtime Manager & Auto-Detection
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 3-4h  
**Dependencies**: Task 3

### Description
Implement RuntimeManager singleton with auto-detection of installed CLIs and BackendRegistry factory.

### Acceptance Criteria
- [ ] `RuntimeManager` singleton com `RUNTIME_COMMANDS` mapeando 10 CLIs
- [ ] `detect_installed_runtimes()`: usa `shutil.which()` para cada CLI; cache em `~/.polybot/runtimes.json`
- [ ] `get_backend_for_runtime(name)`: retorna instância via `BackendRegistry`
- [ ] `execute_task(task)`: orquestra claim → workdir → backend → track → finalize
- [ ] Env var overrides: `MULTICA_CLAUDE_PATH`, `MULTICA_OPENCODE_PATH`, etc. (padrão Multica)
- [ ] Fallback ordenado: se runtime preferido não disponível, tenta próximo na lista do agent
- [ ] `BackendRegistry`: `register(name, backend_class)` e `get(name)`; permite adicionar runtimes dinamicamente

### Files to Create
- `agents/runtime/manager.py`
- `agents/runtime/registry.py`

---

## Task 4: Backend Implementations — Claude + OpenCode + Generic
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 6-8h  
**Dependencies**: Task 3, Task 3b

### Description
Implement CLI spawners for Claude Code and OpenCode with streaming parsers. Criar GenericBackend base para facilitar adicionar novos runtimes.

### Acceptance Criteria
- [ ] `ClaudeBackend` spawns `claude -p --output-format stream-json`
- [ ] `OpencodeBackend` spawns `opencode run --format json`
- [ ] `GenericBackend` base class com parser configurável (command, output_format, parser_config)
- [ ] Todos implementam `AgentBackend` interface
- [ ] Line-by-line stdout parser extracts Message objects
- [ ] Timeout handling kills subprocess after `opts.timeout`
- [ ] Result future is resolved when process exits
- [ ] Error handling for: runtime not installed, invalid args, process crash
- [ ] Unit tests for parsers (mock stdout)
- [ ] Arquitetura permite adicionar novos runtimes com ~100 linhas cada (via GenericBackend ou subclass)

### Files to Create
- `agents/runtime/backend.py` — AgentBackend ABC
- `agents/runtime/claude_backend.py`
- `agents/runtime/opencode_backend.py`
- `agents/runtime/generic_backend.py` — base configurable backend
- `agents/runtime/version.py` — CLI version detection

### Files to Modify
- `agents/runtime/__init__.py`

---

## Task 5: Execution Environment
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 3-4h  
**Dependencies**: Task 3

### Description
Prepare isolated workdir for each task with context files and skills.

### Acceptance Criteria
- [ ] `ExecutionEnvironment.prepare()` creates workdir at `~/polybot_workspaces/{workspace_id}/{task_id}/`
- [ ] Creates subdirectory structure: `workdir/`, `output/`, `logs/`
- [ ] Writes `workdir/AGENTS.md` from agent.system_prompt
- [ ] Writes `workdir/SOUL.md` from agent config (persona)
- [ ] Writes `workdir/COMMANDS.md` from agent custom commands
- [ ] Writes `workdir/.skills/{skill.name}.md` for each linked skill
- [ ] Sets custom env vars in workdir
- [ ] Cleans up old workspaces (>7 days) on init

### Files to Create
- `agents/runtime/execenv.py`

---

## Task 6: Prompt Builder
**Priority**: P1 (Important)  
**Estimated Effort**: 1-2h  
**Dependencies**: Task 3

### Description
Construct task prompts based on market data.

### Acceptance Criteria
- [ ] `build_task_prompt(market, agent)` returns formatted prompt
- [ ] Includes: question, yes/no prices, volume, resolution date
- [ ] Includes instructions: research → gather data → calculate → JSON response
- [ ] Specifies required JSON format: probability, confidence, reasoning, sources
- [ ] Mentions available skills in `.skills/` directory

### Files to Create
- `agents/runtime/prompt_builder.py`

---

## Task 7: Execution Tracker
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 3-4h  
**Dependencies**: Task 2, Task 3

### Description
Consume agent message stream and persist to DB in real-time. Implementa task lifecycle com claim.

### Acceptance Criteria
- [ ] `ExecutionTracker.claim(log_id, runtime)` marca execution_log como `claimed`; retorna False se já claimed (previne race)
- [ ] `ExecutionTracker.track(log_id, session)` consumes AsyncIterator[Message]
- [ ] Each message becomes a step in `execution_steps` with sequential `seq`
- [ ] Step types mapped correctly: text→TEXT, tool_use→TOOL_USE, etc.
- [ ] `ExecutionTracker.finalize(log_id, result)` updates `execution_logs` with result
- [ ] Handles async errors gracefully (logs as ERROR step)
- [ ] Token usage captured when available in Result
- [ ] Dashboard acessa steps via polling HTTP `GET /api/executions/:id/steps`

### Files to Create
- `agents/tracker.py`

---

## Task 8: Agent Registry + Classifier
**Priority**: P1 (Important)  
**Estimated Effort**: 4-5h  
**Dependencies**: Task 2

### Description
Market-to-agent matching and agent lifecycle management.

### Acceptance Criteria
- [ ] `AgentRegistry` loads agents from DB via `AgentRepository`
- [ ] `select_agent_for_market(market)` returns matching agent(s)
  - Priority 1: keyword triggers from agent config
  - Priority 2: default agent
  - Priority 3: ensemble if multiple match
- [ ] `Classifier` extracts keywords from market.question
- [ ] Registry respects `is_active` and `is_archived` filters
- [ ] Concurrency limit check (`max_concurrent_tasks`)

### Files to Create
- `agents/registry.py`
- `agents/classifier.py`

---

## Task 9: Scanner Integration
**Priority**: P0 (Critical Path)  
**Estimated Effort**: 4-6h  
**Dependencies**: Task 3b, Task 4, Task 5, Task 6, Task 7, Task 8

### Description
Refactor scanner to dispatch tasks via AgentRuntime (RuntimeManager) instead of spawning agents diretamente.

### Acceptance Criteria
- [ ] `Scanner` initializes `RuntimeManager`, `AgentRegistry`, `ExecutionTracker`
- [ ] For each value market:
  - Select agent via registry
  - Delega execução ao `RuntimeManager.execute_task(task)`
  - RuntimeManager orquestra: claim → workdir → backend → track → finalize
  - Recebe Result com probability, confidence, reasoning
- [ ] Decision gate usa resultado do agent
- [ ] Fallback para agents legados se runtime falhar (todos os runtimes do agent esgotados)
  - Log failure reason
  - Continue com `sports_analyst`, `esports_analyst`, `odds_analyst`
- [ ] Manter deduplication e alert logic existentes
- [ ] Scanner não spawna subprocess diretamente — sempre via RuntimeManager

### Files to Modify
- `scanner.py` — major refactor
- `main.py` — wire new components

---

## Task 10: Dashboard API Endpoints
**Priority**: P1 (Important)  
**Estimated Effort**: 3-4h  
**Dependencies**: Task 2

### Description
Add REST API endpoints for agents, skills, executions.

### Acceptance Criteria
- [ ] `GET /api/agents` — list all agents
- [ ] `POST /api/agents` — create agent
- [ ] `GET /api/agents/:id` — get agent
- [ ] `PUT /api/agents/:id` — update agent
- [ ] `DELETE /api/agents/:id` — delete agent
- [ ] `GET /api/skills` — list all skills
- [ ] `POST /api/skills` — create skill
- [ ] `GET /api/skills/:id` — get skill
- [ ] `PUT /api/skills/:id` — update skill
- [ ] `DELETE /api/skills/:id` — delete skill
- [ ] `GET /api/executions` — list executions (with pagination, filter by status/agent)
- [ ] `GET /api/executions/:id` — get execution detail
- [ ] `GET /api/executions/:id/steps` — get execution steps
- [ ] CORS enabled for all new endpoints

### Files to Modify
- `api.py` — add new routes

---

## Task 11: Dashboard Frontend — Agents Page
**Priority**: P1 (Important)  
**Estimated Effort**: 4-5h  
**Dependencies**: Task 10

### Description
React page for CRUD of agents.

### Acceptance Criteria
- [ ] `AgentsPage` with list view (AgentCard grid)
- [ ] `AgentForm` modal for create/edit
  - Fields: name, runtime (dropdown), model (dropdown), system_prompt (textarea), skills (multi-select), max_concurrent_tasks, custom_args, custom_env, active toggle
- [ ] `useAgents` hook with TanStack Query (CRUD operations)
- [ ] Navigation link in sidebar

### Files to Create
- `frontend/src/pages/AgentsPage.tsx`
- `frontend/src/components/agents/AgentCard.tsx`
- `frontend/src/components/agents/AgentForm.tsx`
- `frontend/src/hooks/useAgents.ts`

### Files to Modify
- `frontend/src/App.tsx` — add route
- `frontend/src/components/layout/` — add nav links

---

## Task 12: Dashboard Frontend — Skills Page
**Priority**: P1 (Important)  
**Estimated Effort**: 3-4h  
**Dependencies**: Task 10

### Description
React page for CRUD of skills.

### Acceptance Criteria
- [ ] `SkillsPage` with list view (SkillList sidebar)
- [ ] `SkillEditor` for create/edit skill markdown
  - Fields: name, description, content (textarea with markdown preview)
- [ ] `useSkills` hook with TanStack Query
- [ ] Navigation link in sidebar

### Files to Create
- `frontend/src/pages/SkillsPage.tsx`
- `frontend/src/components/skills/SkillEditor.tsx`
- `frontend/src/components/skills/SkillList.tsx`
- `frontend/src/hooks/useSkills.ts`

### Files to Modify
- `frontend/src/App.tsx` — add route

---

## Task 13: Dashboard Frontend — Executions Page
**Priority**: P1 (Important)  
**Estimated Effort**: 4-5h  
**Dependencies**: Task 10

### Description
React page for monitoring agent executions.

### Acceptance Criteria
- [ ] `ExecutionsPage` with table/list of executions
  - Columns: market, agent, runtime, status, duration
  - Filters: status, agent, date range
- [ ] `ExecutionDetail` view with:
  - Result summary (probability, confidence, reasoning)
  - `ExecutionTimeline` with steps (status, tool_use, tool_result, thinking, text)
  - Token usage
  - Sources
- [ ] `useExecutions` hook with TanStack Query
- [ ] Navigation link in sidebar

### Files to Create
- `frontend/src/pages/ExecutionsPage.tsx`
- `frontend/src/components/executions/ExecutionTimeline.tsx`
- `frontend/src/components/executions/ExecutionDetail.tsx`
- `frontend/src/hooks/useExecutions.ts`

### Files to Modify
- `frontend/src/App.tsx` — add route

---

## Task 14: Default Skills
**Priority**: P2 (Nice to Have)  
**Estimated Effort**: 2-3h  
**Dependencies**: Task 2

### Description
Create pre-built skills for common market types.

### Acceptance Criteria
- [ ] `weather_skill.md` — instructions for weather market research (OpenWeatherMap API)
- [ ] `commodity_skill.md` — instructions for commodity markets (Yahoo Finance / Alpha Vantage)
- [ ] `news_search_skill.md` — instructions for news research (web search, authoritative sources)
- [ ] Migration script or seed data to insert default skills into DB
- [ ] Dynamic `AGENTS.md` generation from agent config + linked skills

### Files to Create
- `agents/skills/weather_skill.md`
- `agents/skills/commodity_skill.md`
- `agents/skills/news_search_skill.md`
- `scripts/seed_skills.py`

---

## Task 15: Circuit Breaker + Resilience
**Priority**: P1 (Important)  
**Estimated Effort**: 2-3h  
**Dependencies**: Task 4

### Description
Add circuit breaker for runtimes and graceful error handling.

### Acceptance Criteria
- [ ] `CircuitBreaker` class tracks failures per runtime
- [ ] After 3 consecutive failures → 5min cooldown
- [ ] After cooldown → half-open (1 test request)
- [ ] Scanner detects circuit open and skips runtime
- [ ] Failure reasons categorized: timeout, agent_error, runtime_offline, parse_error

### Files to Create
- `agents/circuit_breaker.py` (refactor existing if any)

---

## Task 16: Integration Test + Documentation
**Priority**: P1 (Important)  
**Estimated Effort**: 3-4h  
**Dependencies**: All above tasks

### Description
End-to-end test and documentation update.

### Acceptance Criteria
- [ ] Integration test with real weather market (Claude Code)
- [ ] Task dispatch latency <2s verified
- [ ] Fallback to legacy agents verified
- [ ] `docs/architecture.md` updated with runtime module
- [ ] `docs/apis.md` updated with new endpoints
- [ ] `docs/changelog.md` updated with [Unreleased] entries
- [ ] `AGENTS.md` updated with new env vars (WORKSPACE_ROOT, etc.)

### Files to Modify
- `docs/architecture.md`
- `docs/apis.md`
- `docs/changelog.md`
- `AGENTS.md`
- `config.py` — add new settings (workspace_root, runtime timeouts)

---

## Execution Order Summary

```
Week 1
├── Task 1: DB Schema
├── Task 2: Repositories
├── Task 3: Runtime Models
├── Task 3b: Runtime Manager & Auto-Detection
├── Task 4: Backend Implementations
└── Task 5: Execution Environment

Week 2
├── Task 6: Prompt Builder
├── Task 7: Execution Tracker
├── Task 8: Agent Registry + Classifier
└── Task 15: Circuit Breaker

Week 3
├── Task 9: Scanner Integration
└── Task 10: Dashboard API Endpoints

Week 4
├── Task 11: Dashboard Frontend — Agents
├── Task 12: Dashboard Frontend — Skills
└── Task 13: Dashboard Frontend — Executions

Week 5
├── Task 14: Default Skills
└── Task 16: Integration Test + Documentation
```

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Any runtime CLI changes output format | Medium | High | GenericBackend + abstract parser; easy to swap |
| No runtimes installed in production | Low | High | Fallback to legacy agents; dashboard warns operator |
| Auto-detect slow on startup | Low | Medium | Cache em `~/.polybot/runtimes.json`; refresh manual opcional |
| DB migrations fail in production | Low | High | Idempotent schema; test on copy first |
| Scanner refactor breaks existing flow | Medium | High | Keep legacy path as fallback; extensive testing |
| Frontend bundle size increases | Medium | Low | Code split new pages; lazy load |
| Task timeout floods DB with steps | Low | Medium | Limit max steps per execution; cleanup old logs |
