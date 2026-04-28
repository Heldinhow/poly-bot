# Roadmap: Agent Runtime Multica-Style para Poly-Bot

## Visão

Transformar o poly-bot em um **Agent Runtime** no estilo Multica, onde cada mercado promissor gera uma *task* que é despachada para um **coding agent** (Claude Code, OpenClaw, Hermes, OpenCode). O agent executa de forma isolada, com prompt e skills configuráveis, realiza pesquisa externa via tools (web search, bash, APIs), toma decisões documentadas e reporta resultados — tudo rastreável e gerenciável via dashboard.

> **Regra de ouro**: *Cada aposta é uma task. Cada task é executada por um agent configurável. Cada execução é rastreável.*

---

## Motivação

Hoje o poly-bot tem agents de análise embarcados em código Python (`sports_analyst.py`, etc.) que usam apenas o conhecimento estático do LLM. Isso limita o bot a tópicos onde o LLM já é bem informado.

Com um runtime de coding agents, cada mercado ganha um **agent dedicado** que pode:
- Abrir um browser e pesquisar a previsão do tempo em Seul
- Consultar APIs de commodities para o preço do WTI
- Buscar notícias recentes sobre um candidato político
- Calcular probabilidades com dados reais em mãos

Tudo isso usando os mesmos runtimes que o Multica suporta: **Claude Code**, **OpenClaw**, **Hermes Agent** e **OpenCode**.

---

## Arquitetura Proposta

### Conceito Central: Task-per-Market + Agent Runtime

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         scanner.py (orquestrador / task dispatcher)          │
│                                                                              │
│  Para cada mercado promissor:                                               │
│  1. Cria uma Task (market_id, question, timestamp)                          │
│  2. Consulta AgentRegistry → qual agent + runtime usar                      │
│  3. Prepara exec env isolado (workdir + context files + skills)             │
│  4. Spawna o coding agent CLI (claude / openclaw / hermes / opencode)       │
│  5. Faz streaming do progresso → salva em execution_logs                    │
│  6. Recebe resultado (probability, confidence, reasoning)                   │
│  7. Decision Gate com dados enriquecidos                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐
            │  Claude  │    │OpenClaw  │    │  Hermes  │
            │  Code    │    │          │    │  Agent   │
            └──────────┘    └──────────┘    └──────────┘
                    ▼               ▼               ▼
            ┌──────────────────────────────────────────┐
            │     Agent Prompt + Skills (AGENTS.md)    │
            │  "Você é um analista de mercados...      │
            │   Pesquise dados reais antes de calcular"│
            └──────────────────────────────────────────┘
```

### Runtimes Suportados (4)

| Runtime | CLI | Protocolo | Modelos |
|---------|-----|-----------|---------|
| **Claude Code** | `claude` | `stream-json` (stdout) | Claude Sonnet, Opus, Haiku |
| **OpenClaw** | `openclaw` | JSON-RPC via stdio | Configurável por agent |
| **Hermes Agent** | `hermes` | ACP (JSON-RPC) | Configurável por agent |
| **OpenCode** | `opencode` | `run --format json` | Vários providers (OpenAI, Anthropic, etc.) |

> **Não suportados**: Codex, Copilot, Cursor, Gemini, Pi, Kimi, Kiro.

---

## Fases de Implementação

---

### Fase 1: Agent Runtime Core (Semana 1-2)

**Objetivo**: Ter um backend que spawna coding agents e se comunica com eles.

#### 1.1 `agents/runtime/` — Backend Unificado

Criar um backend Go/Python que implementa a interface unificada do Multica:

```python
class AgentBackend(ABC):
    async def execute(
        self,
        ctx: ExecutionContext,
        prompt: str,
        opts: ExecOptions
    ) -> Session:
        """Spawna o agent CLI e retorna sessão com streaming."""

@dataclass
class ExecOptions:
    cwd: str                    # diretório de trabalho isolado
    model: str                  # modelo a usar (ex: claude-sonnet-4-6)
    system_prompt: str          # instruções do agent (inline)
    timeout: timedelta          # timeout da task (default: 20min)
    resume_session_id: str      # para retomar sessão anterior
    custom_args: list[str]      # flags extras do CLI

@dataclass
class Session:
    messages: AsyncIterator[Message]  # streaming de eventos
    result: asyncio.Future[Result]    # resultado final

class MessageType(Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"         # agent chamou uma tool
    TOOL_RESULT = "tool_result"   # resultado da tool
    STATUS = "status"             # running, idle, etc.
    ERROR = "error"
    LOG = "log"
```

Implementações concretas:
- `ClaudeBackend`: spawna `claude -p --output-format stream-json`
- `OpenclawBackend`: spawna `openclaw agent` com JSON-RPC
- `HermesBackend`: spawna `hermes acp` com ACP handshake
- `OpencodeBackend`: spawna `opencode run --format json`

#### 1.2 `agents/runtime/execenv.py` — Ambiente Isolado

Para cada task, criar um diretório isolado com:

```
~/polybot_workspaces/
└── {workspace_id}/
    └── {task_id_short}/
        ├── workdir/              # cwd do agent
        │   ├── AGENTS.md         # instruções do agent (do DB)
        │   ├── SOUL.md           # persona/voz (do DB)
        │   ├── COMMANDS.md       # comandos customizados (do DB)
        │   └── .skills/          # skills injetadas
        │       ├── weather_skill.md
        │       └── commodity_skill.md
        ├── output/               # artefatos gerados pelo agent
        └── logs/                 # logs da execução
```

O agent executa dentro de `workdir/`, enxergando os arquivos de contexto como o Multica faz.

#### 1.3 `agents/runtime/prompt_builder.py` — Prompt da Task

Constrói o prompt inicial que o agent recebe. Baseado no tipo de mercado:

```python
def build_task_prompt(market: Market, agent: AgentConfig) -> str:
    return f"""You are running as an analysis agent for a Polymarket betting bot.

Your task is to evaluate this prediction market and estimate the true probability.

## Market
Question: {market.question}
Yes price: {market.yes_price:.2%}
No price: {market.no_price:.2%}
Volume 24h: ${market.volume_24h:,.0f}
Resolution date: {market.resolution_date}

## Instructions
1. First, RESEARCH the topic using available tools (web search, APIs, bash)
2. Gather real-time data relevant to this market
3. Calculate the TRUE probability of the outcome
4. Respond with JSON:
   {{"probability": 0.XX, "confidence": 0.XX, "reasoning": "...", "sources": ["..."]}}
"""
```

---

### Fase 2: Tracking de Execução (Semana 3)

**Objetivo**: Cada execução de agent é rastreável passo a passo.

#### 2.1 Tabela `execution_logs`

```sql
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    agent_id UUID REFERENCES agents(id),
    runtime TEXT NOT NULL,              -- claude | openclaw | hermes | opencode
    model TEXT,
    
    -- Status pipeline
    status TEXT NOT NULL DEFAULT 'queued',  -- queued | running | completed | failed | cancelled
    
    -- Timing
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INT,
    
    -- Resultado
    probability DECIMAL(5,4),           -- 0.0000 a 1.0000
    confidence DECIMAL(5,4),
    reasoning TEXT,
    sources JSONB,
    raw_output TEXT,                    -- output completo do agent
    
    -- Error tracking
    error_message TEXT,
    failure_reason TEXT,                -- timeout | agent_error | runtime_offline
    
    -- Token usage (por runtime que reportar)
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

#### 2.2 Tabela `execution_steps`

Tracking granular de cada passo do agent:

```sql
CREATE TABLE execution_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_log_id UUID REFERENCES execution_logs(id),
    seq INT NOT NULL,                   -- ordem do passo
    
    step_type TEXT NOT NULL,            -- text | thinking | tool_use | tool_result | error | status
    content TEXT,                       -- texto/thinking do agent
    
    -- Para tool_use / tool_result
    tool_name TEXT,                     -- ex: web_search, bash, fetch_url
    tool_input JSONB,                   -- parâmetros da tool
    tool_output TEXT,                   -- resultado da tool
    tool_call_id TEXT,                  -- ID para parear use <-> result
    
    -- Metadata
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_execution_steps_log ON execution_steps(execution_log_id, seq);
```

#### 2.3 `ExecutionTracker` — Streaming para DB

```python
class ExecutionTracker:
    """Consome o stream de mensagens do agent e persiste em tempo real."""
    
    async def track(self, log_id: str, session: Session):
        seq = 0
        async for msg in session.messages:
            seq += 1
            await self._save_step(log_id, seq, msg)
            
    async def finalize(self, log_id: str, result: Result):
        await self._update_log(log_id, result)
```

Isso permite ver em tempo real o que o agent está fazendo: "Tool #1: web_search('previsão tempo Seul')", "Tool #2: fetch_url('...')", etc.

---

### Fase 3: Dashboard — Gestão de Agents e Skills (Semana 4-5)

**Objetivo**: Interface web para criar, editar e monitorar agents.

#### 3.1 Nova Aba: "Agents" (CRUD)

Tela de gestão de agents no dashboard React:

```
┌─────────────────────────────────────────────────────────────┐
│  Agents                                      [+ New Agent]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ WeatherBot  │  │ OilAnalyst  │  │ ElectionBot │         │
│  │ Claude Code │  │ OpenClaw    │  │ Hermes      │         │
│  │ Model: ...  │  │ Model: ...  │  │ Model: ...  │         │
│  │ [Edit] [▶]  │  │ [Edit] [▶]  │  │ [Edit] [▶]  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Formulário de criação/edição**:
- **Name**: identificador único (ex: "WeatherBot")
- **Runtime**: dropdown (Claude Code | OpenClaw | Hermes | OpenCode)
- **Model**: dropdown dinâmico baseado no runtime selecionado
- **System Prompt**: textarea com o prompt base do agent
- **Skills**: multi-select das skills disponíveis
- **Max Concurrent Tasks**: número máximo de tasks paralelas
- **Custom Args**: flags extras do CLI (array de strings)
- **Custom Env**: variáveis de ambiente (key-value)
- **Active**: toggle on/off

**Tabela `agents`**:
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    
    -- Runtime config
    runtime TEXT NOT NULL CHECK (runtime IN ('claude', 'openclaw', 'hermes', 'opencode')),
    model TEXT,
    system_prompt TEXT,
    
    -- Skills vinculadas
    skills UUID[] DEFAULT '{}',
    
    -- Limits
    max_concurrent_tasks INT DEFAULT 1,
    
    -- Advanced
    custom_args TEXT[] DEFAULT '{}',
    custom_env JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_archived BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.2 Nova Aba: "Skills" (Editor)

Editor de skills no padrão Multica — cada skill é um **arquivo markdown** que é injetado no contexto do agent:

```
┌─────────────────────────────────────────────────────────────┐
│  Skills                                      [+ New Skill]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ Sidebar          │  │ Editor                         │  │
│  │ ─────────────    │  │ ┌────────────────────────────┐ │  │
│  │ weather_skill    │  │ │ Name: weather_research     │ │  │
│  │ commodity_skill  │  │ │                            │ │  │
│  │ sports_injuries  │  │ │ ## Weather Research        │ │  │
│  │ news_search      │  │ │                            │ │  │
│  │                  │  │ │ When researching weather   │ │  │
│  │                  │  │ │ markets:                   │ │  │
│  │                  │  │ │ 1. Use OpenWeatherMap API  │ │  │
│  │                  │  │ │ 2. Check forecast for the  │ │  │
│  │                  │  │ │    exact date              │ │  │
│  │                  │  │ │ 3. Note confidence levels  │ │  │
│  │                  │  │ │                            │ │  │
│  │                  │  │ │ [Save] [Delete]            │ │  │
│  │                  │  │ └────────────────────────────┘ │  │
│  └──────────────────┘  └────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Tabela `skills`**:
```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,           -- conteúdo markdown da skill
    
    -- Metadados
    file_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de junção
CREATE TABLE agent_skills (
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);
```

**Como funciona a injeção de skills**:
- Quando uma task é despachada, o `execenv.py` escreve cada skill vinculada ao agent como um arquivo `.md` dentro de `.skills/`
- O prompt do agent inclui: *"You have access to the following skills in .skills/ directory. Read them before proceeding."*
- Cada runtime lê os arquivos conforme sua convenção:
  - **Claude Code**: lê `AGENTS.md`, `.skills/*.md` automaticamente
  - **OpenClaw**: skills passadas via `--skill` ou diretório
  - **Hermes**: injetado no system prompt ou via ACP
  - **OpenCode**: diretório de skills configurado

#### 3.3 Nova Aba: "Executions" (Monitoramento)

Visualização de todas as execuções de agents:

```
┌─────────────────────────────────────────────────────────────┐
│  Executions                                    [Filters ▼]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Market                          Agent      Runtime  Status │
│  ─────────────────────────────────────────────────────────  │
│  Temp em Seul >25°C?             WeatherBot Claude   ✅ Done │
│  WTI > $80 na sexta?             OilAnalyst OpenClaw ✅ Done │
│  Trump ganha 2028?               ElectionBot Hermes  ⏳ Run  │
│  Lakers vence hoje?              SportsBot  Claude   ❌ Fail │
│                                                             │
│  [Click para ver detalhes]                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Tela de detalhes da execução**:
```
┌─────────────────────────────────────────────────────────────┐
│  Execution #abc123 — Temp em Seul >25°C?                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent: WeatherBot (Claude Code)                            │
│  Model: claude-sonnet-4-6                                   │
│  Duration: 12.3s                                            │
│  Status: ✅ Completed                                       │
│                                                             │
│  Result:                                                    │
│  Probability: 0.12 (12%)                                    │
│  Confidence: 0.85                                           │
│  Reasoning: "OpenWeather shows max 23°C for Seoul..."       │
│                                                             │
│  Steps Timeline:                                            │
│  ─────────────────────────────────────────────────────────  │
│  1. [STATUS]  Agent started                                 │
│  2. [TOOL]    web_search("Seoul weather forecast tomorrow") │
│  3. [RESULT]  3 results found                               │
│  4. [TOOL]    fetch_url("openweather.com/seoul")            │
│  5. [RESULT]  Max temp: 23°C, partly cloudy                 │
│  6. [THINK]   "23°C is 2 degrees below 25°C threshold..."   │
│  7. [TEXT]    {"probability": 0.12, ...}                    │
│  8. [STATUS]  Agent completed                               │
│                                                             │
│  Sources:                                                   │
│  - OpenWeatherMap (confidence: 0.9)                         │
│  - weather.com (confidence: 0.8)                            │
│                                                             │
│  Token Usage: 1,234 in / 567 out                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Fase 4: Integração Scanner + Runtime (Semana 6)

**Objetivo**: O scanner despacha tasks para o runtime de agents.

#### 4.1 Novo fluxo do Scanner

```python
class Scanner:
    def __init__(self, ...):
        self._runtime = AgentRuntime()        # NOVO
        self._registry = AgentRegistry()      # NOVO: lê do DB
        self._tracker = ExecutionTracker()    # NOVO
    
    def scan(self) -> int:
        markets = self._client.fetch_active_markets(limit=200)
        value_bets = self._filter_markets(markets)
        
        for market in value_bets:
            # 1. Seleciona o agent mais adequado (por classificação ou manual)
            agent = self._registry.select_agent_for_market(market)
            
            # 2. Cria task e despacha para o runtime
            task = Task(market=market, agent=agent)
            result = self._runtime.run(task)
            
            # 3. Decision gate com o resultado do agent
            if result.probability:
                edge = self._decision_gate.evaluate(
                    probability=result.probability,
                    confidence=result.confidence,
                    market_price=market.implied_prob
                )
                if edge == "ACCEPT":
                    self._portfolio.record_bet(market, result)
```

#### 4.2 `AgentRegistry.select_agent_for_market()`

Regra de seleção (configurável):
1. Se o mercado bate com `triggers` de um agent específico → usa esse agent
2. Senão, usa o agent `default` (análise genérica)
3. Se múltiplos agents batem → roda todos em paralelo e agrega (ensemble)

---

### Fase 5: Política de Skills Padrão (Semana 7)

**Objetivo**: Skills pré-criadas para os tipos de mercado mais comuns.

#### 5.1 Skills Iniciais

**`weather_skill.md`**:
```markdown
# Weather Market Research

When analyzing weather prediction markets:

1. Identify the exact location (city, country) from the market question
2. Identify the exact date from the market question
3. Use OpenWeatherMap or WeatherAPI to fetch the forecast
4. Report: temperature, conditions, precipitation probability
5. Note forecast reliability (24h vs 7-day forecasts differ in accuracy)

API Key: Use env var OPENWEATHER_API_KEY
```

**`commodity_skill.md`**:
```markdown
# Commodity Market Research

When analyzing commodity markets (oil, gold, etc.):

1. Identify the exact commodity and benchmark (WTI, Brent, spot, etc.)
2. Use Yahoo Finance or Alpha Vantage for current spot price
3. Check recent trend (24h, 7d)
4. Note relevant news (OPEC decisions, geopolitical events)

API Key: Use env var ALPHA_VANTAGE_API_KEY
```

**`news_search_skill.md`**:
```markdown
# News Research

When you need recent information about an event:

1. Use web_search to find the latest news
2. Check authoritative sources (Reuters, Bloomberg, AP)
3. Note publication dates — old news may be irrelevant
4. Summarize key facts that affect the market outcome
```

#### 5.2 AGENTS.md Padrão

Cada agent tem um `AGENTS.md` gerado dinamicamente do banco:

```markdown
# Agent: {agent.name}

## Role
{agent.description}

## Runtime
{agent.runtime} ({agent.model})

## Instructions
{agent.system_prompt}

## Available Skills
{for skill in agent.skills}
- {skill.name}: {skill.description}
{/for}

## Important Rules
1. Always research with tools before calculating probability
2. Cite your sources
3. Respond in the required JSON format
```

---

## Estrutura de Diretórios Final

```
poly-bot/
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent legacy (mantido)
│   ├── runtime/                   # NOVO: runtime de coding agents
│   │   ├── __init__.py
│   │   ├── backend.py             # AgentBackend interface
│   │   ├── claude_backend.py      # Claude Code integration
│   │   ├── openclaw_backend.py    # OpenClaw integration
│   │   ├── hermes_backend.py      # Hermes ACP integration
│   │   ├── opencode_backend.py    # OpenCode integration
│   │   ├── execenv.py             # Isolated workdir prep
│   │   ├── prompt_builder.py      # Task prompt construction
│   │   ├── models.py              # dataclasses (Session, Result, Message)
│   │   └── version.py             # CLI version detection
│   ├── registry.py                # AgentRegistry (DB-backed)
│   ├── classifier.py              # Market-to-Agent matching
│   ├── tracker.py                 # ExecutionTracker (DB streaming)
│   ├── cache.py                   # Research cache (mantido)
│   └── circuit_breaker.py         # Resiliência (mantido)
│
├── db/
│   ├── schema.sql                 # + agents, skills, execution_logs, execution_steps
│   └── repository.py              # + AgentRepository, SkillRepository, ExecutionRepository
│
├── scanner.py                     # refatorado: task dispatcher
├── config.py                      # + runtime paths, API keys
│
├── frontend/                      # React dashboard (existente)
│   └── src/
│       ├── components/
│       │   ├── agents/            # NOVO: AgentCard, AgentForm, AgentList
│       │   ├── skills/            # NOVO: SkillEditor, SkillList
│       │   ├── executions/        # NOVO: ExecutionTimeline, ExecutionDetail
│       │   └── layout/
│       ├── hooks/
│       │   ├── useAgents.ts       # CRUD agents
│       │   ├── useSkills.ts       # CRUD skills
│       │   └── useExecutions.ts   # list + detail
│       └── pages/
│           ├── AgentsPage.tsx       # NOVO
│           ├── SkillsPage.tsx       # NOVO
│           └── ExecutionsPage.tsx   # NOVO
│
└── docs/
    └── roadmap.md                 # este arquivo
```

---

## Exemplo de Execução Completa

### Mercado: "Temperatura máxima em Seul > 25°C amanhã?"

**Passo 1 — Seleção de Agent**:
```python
registry.select_agent_for_market("Temperatura máxima em Seul > 25°C amanhã?")
# → Agent(name="WeatherBot", runtime="claude", model="claude-sonnet-4-6")
```

**Passo 2 — Preparação do Ambiente**:
```python
execenv.prepare(
    workdir="~/polybot_workspaces/ws1/abc123/workdir/",
    agent=weather_bot,
    skills=["weather_skill.md", "news_search_skill.md"]
)
# Cria workdir/ com AGENTS.md, .skills/weather_skill.md, etc.
```

**Passo 3 — Execução**:
```python
backend = ClaudeBackend(executable="claude")
session = backend.execute(
    prompt=build_task_prompt(market, weather_bot),
    opts=ExecOptions(cwd=workdir, model="claude-sonnet-4-6")
)
```

**Passo 4 — Tracking em Tempo Real**:
```
[STATUS]  running
[TOOL]    web_search: {"query": "Seoul weather forecast tomorrow April 29"}
[RESULT]  5 results
[TOOL]    bash: {"command": "curl -s 'api.openweathermap.org/...'"}
[RESULT]  {"temp_max": 23, "condition": "partly cloudy"}
[THINK]   "23°C max... 2 degrees below threshold..."
[TEXT]    {"probability": 0.12, "confidence": 0.85, "reasoning": "..."}
[STATUS]  completed
```

Cada mensagem é salva em `execution_steps` em tempo real.

**Passo 5 — Resultado Persistido**:
```python
execution_logs:
  id: "abc123"
  status: "completed"
  probability: 0.12
  confidence: 0.85
  reasoning: "OpenWeather shows max 23°C for Seoul on Apr 29"
  sources: ["OpenWeatherMap"]
  input_tokens: 1234
  output_tokens: 567
```

**Passo 6 — Decision Gate**:
- Market implied prob (Yes): 35%
- AI prob: 12%
- Edge: -23% (negativo)
- **Decisão**: REJECT (ou apostar no "No")

---

## Dependências Novas

```
# requirements.txt additions
# CLI tools (instalados separadamente pelo usuário)
# - claude-code (npm)
# - openclaw (npm)
# - hermes (npm/pip)
# - opencode (npm)

# Python libs
watchdog          # monitorar arquivos de skills
python-dotenv     # já usado, mas necessário para runtime env
```

---

## Métricas de Sucesso

| Métrica | Target |
|---------|--------|
| Runtimes registrados | 4/4 (Claude, OpenClaw, Hermes, OpenCode) |
| Tasks completadas com sucesso | >90% |
| Execuções rastreadas (steps) | 100% das tasks |
| Dashboard funcional | CRUD agents + skills + execuções |
| Latência task dispatch | <2s do scanner para o agent iniciar |
| ROI improvement | >15% relativo ao baseline (agents com tools) |

---

## Decisões de Design Importantes

1. **Apenas 4 runtimes**: Claude Code, OpenClaw, Hermes, OpenCode. Sem Codex/Copilot/Cursor/Gemini/Pi/Kimi/Kiro.
2. **Task = Mercado**: cada mercado vira uma task isolada com seu próprio workdir.
3. **Skills são markdown**: no padrão Multica, skills são arquivos `.md` injetados no contexto. Editáveis via dashboard.
4. **Prompt editável por agent**: cada agent tem seu próprio system prompt, editável no dashboard.
5. **Tracking obrigatório**: 100% das execuções logam steps em `execution_steps`. Sem tracking, não há observabilidade.
6. **Execução isolada**: cada task roda em workdir próprio, com variáveis de ambiente isoladas.
7. **Resume de sessão**: suportado via `resume_session_id` (quando o runtime suportar).
8. **Fallback para analysis puro**: se o runtime falhar, o scanner usa os agents legados (sports_analyst, etc.).

---

## Próximos Passos Imediatos

1. [ ] Criar `agents/runtime/backend.py` com a interface AgentBackend
2. [ ] Implementar `ClaudeBackend` (stream-json parser)
3. [ ] Criar `agents/runtime/execenv.py` (workdir + context files + skills injection)
4. [ ] Adicionar tabelas `agents`, `skills`, `agent_skills`, `execution_logs`, `execution_steps`
5. [ ] Criar `ExecutionTracker` com streaming para DB
6. [ ] Refatorar `scanner.py` para despachar tasks para o runtime
7. [ ] Criar páginas no dashboard: Agents, Skills, Executions
8. [ ] Testar com Claude Code em mercado de clima real

---

*Documento atualizado em: 2026-04-28*
*Baseado na arquitetura do runtime de agents do Multica (multica-ai/multica)*
