# Design: Agent Runtime

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         scanner.py (orchestrador / task dispatcher)          │
│                                                                              │
│  Para cada mercado promissor:                                               │
│  1. Cria uma Task (market_id, question, timestamp)                          │
│  2. Consulta AgentRegistry → qual agent + runtime usar                      │
│  3. Solicita execução ao AgentRuntime (Runtime Manager)                     │
│  4. Recebe resultado (probability, confidence, reasoning)                   │
│  5. Decision Gate com dados enriquecidos                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AgentRuntime (Runtime Manager)                          │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ RuntimeManager   │  │ BackendRegistry  │  │ ExecutionTracker │          │
│  │                  │  │                  │  │                  │          │
│  │ detect_runtimes()│  │ register(name,   │  │ track(log_id,    │          │
│  │ get_backend()    │  │   backend_class) │  │   session)       │          │
│  │ execute_task()   │  │ get(name)        │  │ finalize()       │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┬───────────────┐
                    ▼               ▼               ▼               ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
            │  Claude  │    │ OpenCode │    │  Hermes  │    │  Codex   │
            │  Code    │    │          │    │  Agent   │    │          │
            └──────────┘    └──────────┘    └──────────┘    └──────────┘
                    │               │               │               │
                    └───────────────┴───────────────┴───────────────┘
                                    │
                                    ▼
            ┌──────────────────────────────────────────────────────┐
            │     ExecEnv (workdir isolado + AGENTS.md + skills)    │
            └──────────────────────────────────────────────────────┘
```

## Module Design

### 1. `agents/runtime/` — Backend Unificado

#### `models.py`
```python
from abc import ABC
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, AsyncIterator
import asyncio

class MessageType(Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    STATUS = "status"
    ERROR = "error"
    LOG = "log"

@dataclass
class Message:
    type: MessageType
    content: str
    metadata: dict[str, Any] | None = None

@dataclass
class Result:
    probability: float | None = None
    confidence: float | None = None
    reasoning: str = ""
    sources: list[str] = None
    raw_output: str = ""
    error_message: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

@dataclass
class ExecOptions:
    cwd: str
    model: str
    system_prompt: str
    timeout: timedelta = timedelta(minutes=20)
    max_retries: int = 1
    resume_session_id: str | None = None
    custom_args: list[str] = None
    custom_env: dict[str, str] = None

@dataclass
class ExecutionContext:
    task_id: str
    market_id: str
    agent_id: str
    workspace_id: str

class Session:
    def __init__(self):
        self.messages: AsyncIterator[Message] = None
        self.result: asyncio.Future[Result] = asyncio.Future()

class AgentBackend(ABC):
    async def execute(
        self,
        ctx: ExecutionContext,
        prompt: str,
        opts: ExecOptions
    ) -> Session:
        """Spawna o agent CLI e retorna sessão com streaming."""
        raise NotImplementedError
```

#### `manager.py` — Runtime Manager
```python
class RuntimeManager:
    """Singleton que orquestra auto-detect, backend selection e execução."""
    
    RUNTIME_COMMANDS = {
        "claude": "claude",
        "codex": "codex",
        "openclaw": "openclaw",
        "opencode": "opencode",
        "hermes": "hermes",
        "gemini": "gemini",
        "pi": "pi",
        "cursor-agent": "cursor-agent",
        "kimi": "kimi",
        "kiro-cli": "kiro-cli",
    }
    
    def detect_installed_runtimes(self) -> list[str]:
        """Retorna runtimes cujo CLI está no PATH. Cache em ~/.polybot/runtimes.json"""
    
    def get_backend_for_runtime(self, name: str) -> AgentBackend:
        """Factory via BackendRegistry."""
    
    async def execute_task(self, task: Task) -> Result:
        """Orquestra: claim → workdir → backend → track → finalize."""
```

#### `registry.py` — Backend Registry
```python
class BackendRegistry:
    """Factory de backends por nome. Permite registrar novos runtimes dinamicamente."""
    
    def register(self, name: str, backend_class: type[AgentBackend]):
        """Registra um novo backend."""
    
    def get(self, name: str) -> AgentBackend:
        """Retorna instância do backend."""
```

#### `claude_backend.py`
Spawna `claude -p --output-format stream-json`. Parser de stdout linha a linha para extrair `Message` objects.

#### `opencode_backend.py`
Spawna `opencode run --format json`. Similar ao Claude mas com formato JSON diferente.

#### `generic_backend.py`
Base class para novos runtimes. Recebe `command`, `output_format`, `parser_config` como parâmetros. Permite adicionar novos runtimes sem criar arquivo novo.

#### `execenv.py`
```python
class ExecutionEnvironment:
    def prepare(
        self,
        workspace_root: str,
        task_id: str,
        agent: AgentConfig,  # do DB
        skills: list[Skill],  # do DB
    ) -> str:
        """Cria workdir isolado e retorna path."""
```

#### `prompt_builder.py`
```python
def build_task_prompt(market: Market, agent: AgentConfig) -> str:
    """Constrói prompt inicial baseado no mercado."""
```

### 2. `agents/runtime/tracker.py` — Execution Tracker

```python
class ExecutionTracker:
    """Consome stream de mensagens e persiste em tempo real no DB."""
    
    async def claim(self, log_id: str, runtime: str) -> bool:
        """Marca execution_log como 'claimed' por um runtime. Retorna False se já claimed."""
    
    async def track(self, log_id: str, session: Session):
        seq = 0
        async for msg in session.messages:
            seq += 1
            await self._save_step(log_id, seq, msg)
    
    async def finalize(self, log_id: str, result: Result):
        await self._update_log(log_id, result)
```

**Dashboard acessa via polling HTTP:** `GET /api/executions/:id/steps` a cada 5s (padrão existente do dashboard).

### 3. `agents/registry.py` — Agent Registry

```python
class AgentRegistry:
    def __init__(self, repository: AgentRepository):
        self._repo = repository
    
    def select_agent_for_market(self, market: Market) -> list[Agent]:
        """Seleciona agent(s) para o mercado."""
        # 1. Match por triggers
        # 2. Fallback para default
        # 3. Retorna lista (pode ser ensemble)
    
    def get_active_agents(self) -> list[Agent]:
        """Retorna agents ativos."""
```

### 4. `agents/classifier.py` — Market-to-Agent Matching

```python
class MarketClassifier:
    def classify(self, market: Market) -> list[str]:
        """Retorna lista de agent_ids que atendem ao mercado."""
        # Regras baseadas em keywords do market.question
```

## Database Schema

### Tabela `agents`
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    runtime TEXT NOT NULL,  -- nome do CLI: claude, opencode, hermes, codex, etc.
    model TEXT,
    system_prompt TEXT,
    skills UUID[] DEFAULT '{}',
    max_concurrent_tasks INT DEFAULT 1,
    max_retries INT DEFAULT 1,
    custom_args TEXT[] DEFAULT '{}',
    custom_env JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela `skills`
```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    file_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabela `agent_skills`
```sql
CREATE TABLE agent_skills (
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);
```

### Tabela `execution_logs`
```sql
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    agent_id UUID REFERENCES agents(id),
    runtime TEXT NOT NULL,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT,
    probability DECIMAL(5,4),
    confidence DECIMAL(5,4),
    reasoning TEXT,
    sources JSONB,
    raw_output TEXT,
    error_message TEXT,
    failure_reason TEXT,
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    cache_read_tokens BIGINT DEFAULT 0,
    cache_write_tokens BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_execution_logs_market ON execution_logs(market_id);
CREATE INDEX idx_execution_logs_status ON execution_logs(status);
CREATE INDEX idx_execution_logs_agent ON execution_logs(agent_id);
```

### Tabela `execution_steps`
```sql
CREATE TABLE execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_log_id UUID REFERENCES execution_logs(id),
    seq INT NOT NULL,
    step_type TEXT NOT NULL,
    content TEXT,
    tool_name TEXT,
    tool_input JSONB,
    tool_output TEXT,
    tool_call_id TEXT,
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_execution_steps_log ON execution_steps(execution_log_id, seq);
```

## API Endpoints (Backend)

```
GET    /api/agents              → list agents
POST   /api/agents              → create agent
GET    /api/agents/:id          → get agent
PUT    /api/agents/:id          → update agent
DELETE /api/agents/:id          → delete agent

GET    /api/skills              → list skills
POST   /api/skills              → create skill
GET    /api/skills/:id          → get skill
PUT    /api/skills/:id          → update skill
DELETE /api/skills/:id          → delete skill

GET    /api/executions          → list executions (paginated, filterable)
GET    /api/executions/:id      → get execution detail
GET    /api/executions/:id/steps → get execution steps
```

## Frontend Structure

```
frontend/src/
├── components/
│   ├── agents/
│   │   ├── AgentCard.tsx
│   │   ├── AgentForm.tsx
│   │   └── AgentList.tsx
│   ├── skills/
│   │   ├── SkillEditor.tsx
│   │   └── SkillList.tsx
│   ├── executions/
│   │   ├── ExecutionTimeline.tsx
│   │   └── ExecutionDetail.tsx
│   └── layout/
│       └── SidebarNav.tsx      # add Agents, Skills, Executions links
├── hooks/
│   ├── useAgents.ts
│   ├── useSkills.ts
│   └── useExecutions.ts
└── pages/
    ├── AgentsPage.tsx
    ├── SkillsPage.tsx
    └── ExecutionsPage.tsx
```

## Key Design Decisions

### 1. Vendor-neutral runtimes
Auto-detecta todos os CLIs no PATH (até 10). Não limitamos a 4 — o operador usa o que tem instalado. Fallback ordenado: se o preferido não está disponível, tenta o próximo.

### 2. Runtime Manager como camada de abstração
O scanner não spawna CLIs diretamente. Ele delega ao `AgentRuntime` (RuntimeManager), que orquestra: detect → claim → workdir → backend → track. Isso desacopla "quem pede" do "quem executa", seguindo o padrão Multica daemon.

### 3. Task = Mercado
Cada mercado vira uma task isolada com seu próprio workdir.

### 4. Skills são markdown
No padrão Multica, skills são arquivos `.md` injetados no contexto. Editáveis via dashboard.

### 5. Prompt editável por agent
Cada agent tem seu próprio system prompt, editável no dashboard.

### 6. Tracking obrigatório
100% das execuções logam steps em `execution_steps`. Sem tracking, não há observabilidade.

### 7. Execução isolada
Cada task roda em workdir próprio, com variáveis de ambiente isoladas.

### 8. Resume de sessão
Suportado via `resume_session_id` (quando o runtime suportar).

### 9. Fallback para analysis puro
Se o runtime falhar, o scanner usa os agents legados (sports_analyst, etc.).

### 10. Polling HTTP para dashboard
MVP usa polling de 5s (padrão existente). SSE/WebSocket são upgrades futuros sem breaking change.

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runtime language | Python (not Go) | Consistency with existing codebase; no Go expertise in project |
| Async pattern | asyncio subprocess | Standard Python for spawning CLI processes |
| DB schema | Raw SQL + migrations | Consistency with existing `schema.sql` pattern |
| Skill storage | TEXT in PostgreSQL | Simple, versioned, queryable |
| Workdir location | `~/polybot_workspaces/` | Isolated from project, easy to clean up |
| Frontend state | TanStack Query | Already used in existing dashboard |
| Streaming parser | Line-by-line JSON | Simple and robust for CLI stdout |
