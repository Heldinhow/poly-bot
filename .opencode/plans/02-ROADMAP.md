# Roadmap: Poly-Bot Agent Runtime

## Phase 1: Foundation (Week 1)
**Goal**: Database schema and data access layer for the new runtime.

- DB Schema: `agents`, `skills`, `agent_skills`, `execution_logs`, `execution_steps`
- Repositories: `AgentRepository`, `SkillRepository`, `ExecutionRepository`
- Update `db/schema.sql` and `db/repository.py`

## Phase 2: Agent Runtime Core (Week 1-2)
**Goal**: Backend that spawns coding agents and communicates with them.

- Runtime models: `Session`, `Result`, `Message`, `ExecOptions`, `ExecutionContext`
- Backend interface: `AgentBackend` ABC
- Implementations: `ClaudeBackend`, `OpencodeBackend` (MVP — 2 of 4)
- ExecEnv: Isolated workdir prep with AGENTS.md, SOUL.md, COMMANDS.md, .skills/
- Prompt Builder: Task prompt construction per market type

## Phase 3: Execution Tracking (Week 2)
**Goal**: Every agent execution is traceable step by step.

- `ExecutionTracker`: Stream consumer + DB persistence
- Real-time step logging to `execution_steps`
- Finalize execution results in `execution_logs`

## Phase 4: Agent Registry (Week 3)
**Goal**: Market-to-agent matching and agent lifecycle management.

- `AgentRegistry`: DB-backed agent CRUD + selection logic
- `Classifier`: Market-to-agent matching (triggers/rules)
- Registry API endpoints for dashboard

## Phase 5: Scanner Integration (Week 3-4)
**Goal**: Scanner dispatches tasks to the agent runtime.

- Refactor `scanner.py` to use `AgentRuntime`
- `AgentRegistry.select_agent_for_market()` integration
- Decision gate with enriched agent data
- Fallback to legacy agents when runtime fails

## Phase 6: Dashboard — Management & Monitoring (Week 4-5)
**Goal**: Web interface to create, edit and monitor agents.

- API endpoints: `/api/agents`, `/api/skills`, `/api/executions`
- React pages: `AgentsPage`, `SkillsPage`, `ExecutionsPage`
- Components: `AgentCard`, `AgentForm`, `SkillEditor`, `ExecutionTimeline`
- Hooks: `useAgents`, `useSkills`, `useExecutions`

## Phase 7: Default Skills (Week 5)
**Goal**: Pre-built skills for common market types.

- `weather_skill.md`
- `commodity_skill.md`
- `news_search_skill.md`
- Dynamic AGENTS.md generation from DB

## Phase 8: Polish & Validation (Week 6)
**Goal**: Test end-to-end with real market.

- Integration test: Claude Code on real weather market
- Performance: task dispatch latency <2s
- Error handling: runtime offline, timeout, agent error
- Documentation update: `docs/architecture.md`, `docs/apis.md`, `docs/changelog.md`
