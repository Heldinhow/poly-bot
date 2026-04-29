# Design: Execution Live Tracking

## Architecture Overview

```
Agent Backend (claude/opencode)
  │  yield Message(type, content, tool, ...)
  ▼
AgentRunner.analyze_market()
  │  session = backend.execute()
  │  tracker.track(log_id, session)  ← async consume
  ▼
ExecutionTracker.track()
  │  async for msg in session.messages:
  │    _save_step(log_id, seq, msg)      → DB
  │    _broadcast_step(log_id, msg)      → EventBus  ← NOVO
  ▼
ExecutionEventBus
  │  EXECUTION_STEP event publicado
  ▼
WebSocket: /api/executions/{id}/stream  ← NOVO endpoint
  │  Filtra eventos por execution_log_id
  │  Envia como JSON via WebSocket
  ▼
Frontend: useExecutionStream(executionId)
  │  Conecta WebSocket, buffer de steps
  │  Carrega steps existentes via REST primeiro
  ▼
LiveExecutionCard
  ├── TimelineProgressBar (segmentos coloridos)
  ├── ExecutionTimeline (steps em tempo real)
  └── ExecutionSummary (output final)
```

## Backend Changes

### 1. Novo tipo de evento (`realtime/events.py`)
```python
EXECUTION_STEP = "execution.step"
```
O `ExecutionEvent.data` incluirá:
- `execution_log_id`: UUID string
- `seq`: int
- `step_type`: "text" | "thinking" | "tool_use" | "tool_result" | "error"
- `content`: str | None
- `tool_name`: str | None
- `tool_input`: dict | None
- `tool_output`: str | None

### 2. ExecutionTracker com broadcast (`agents/tracker.py`)
- Receber `event_bus` no construtor (opcional, mantém compatibilidade)
- `_save_step()` → após INSERT no DB, publica `ExecutionEvent(type=EXECUTION_STEP, data={...})` no bus
- O broadcast é fire-and-forget (não bloqueia o tracking se o bus falhar)

### 3. Novo WebSocket endpoint (`api.py`)
- `GET /api/executions/{id}/stream`
- Filtra eventos do EventBus onde `event.data.execution_log_id == id`
- Envia cada step como JSON: `{type: "step", seq, step_type, content, tool_name, tool_input, tool_output}`
- Envia evento final quando status muda para completed/failed: `{type: "status", status: "completed"}`
- Heartbeat a cada 15s: `{type: "ping"}`

### 4. AgentRunner wiring (`agents/runtime/runner.py`)
- Passar `event_bus` para `ExecutionTracker` no construtor
- Nenhuma mudança na lógica de execução

## Frontend Changes

### Novos hooks (`frontend/src/hooks/useExecutionStream.ts`)

```typescript
function useExecutionStream(executionId: string | null): {
  steps: ExecutionStep[];      // todos os steps (histórico + stream)
  status: string | null;        // status atual da execução
  isConnected: boolean;         // WS conectado?
  isLive: boolean;              // ainda está recebendo steps?
}
```

**Funcionamento:**
1. Se `executionId` não é null:
   - Busca steps existentes via `GET /api/executions/{id}/steps` (REST)
   - Conecta WebSocket `ws://localhost:8080/api/executions/{id}/stream`
   - Appends new steps ao buffer local
   - Detecta status final (completed/failed) → fecha WS
   - Reconexão automática com backoff
2. Se `executionId` é null: retorna vazio

### Novos componentes

#### `LiveExecutionCard` (substitui `ExecutionCard` em `ExecutionsPage.tsx`)
- Props: `exec: Execution`
- Estados:
  - `queued`/`claimed`: "Waiting for agent..." placeholder
  - `running`: conecta `useExecutionStream`, mostra timeline live
  - `completed`/`failed`: mostra `ExecutionSummary` + timeline colapsada
- Colapsa/expande via toggle (mantém comportamento atual do clique no header)

#### `TimelineProgressBar`
- Props: `steps: ExecutionStep[]`
- Calcula % de cada tipo e renderiza segmentos coloridos
- Tooltip no hover com "{tipo}: {count}"

#### `ExecutionTimeline`
- Props: `steps: ExecutionStep[]`, `isLive: boolean`
- Lista scrollable com ref para auto-scroll
- Detecta scroll-up do usuário → mostra botão "↓ Latest"

#### `ExecutionSummary`
- Props: `exec: Execution`
- Grid com Probability, Confidence, Edge, Decision
- Reasoning text
- Só renderiza se status for completed

### Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `realtime/events.py` | Adicionar `EXECUTION_STEP` |
| `agents/tracker.py` | Adicionar `event_bus` param + broadcast |
| `agents/runtime/runner.py` | Passar `event_bus` para tracker |
| `api.py` | Novo endpoint `/api/executions/{id}/stream` |
| `main.py` | Passar `event_bus` para `AgentRunner` |
| `frontend/src/hooks/useExecutionStream.ts` | NOVO |
| `frontend/src/components/LiveExecutionCard.tsx` | NOVO |
| `frontend/src/components/TimelineProgressBar.tsx` | NOVO |
| `frontend/src/components/ExecutionTimeline.tsx` | NOVO |
| `frontend/src/components/ExecutionSummary.tsx` | NOVO |
| `frontend/src/pages/ExecutionsPage.tsx` | Usar `LiveExecutionCard` no lugar de `ExecutionCard` |
| `frontend/src/hooks/useExecutions.ts` | Adicionar tipo `Execution` completo (sem raw_output) |

### Cores por step type (Tailwind classes)

| Step Type | Badge bg | Badge text | Bar color |
|-----------|----------|------------|-----------|
| `text` | `bg-emerald-500/20` | `text-emerald-400` | `bg-emerald-500` |
| `thinking` | `bg-violet-500/20` | `text-violet-400` | `bg-violet-500` |
| `tool_use` | `bg-blue-500/20` | `text-blue-400` | `bg-blue-500` |
| `tool_result` | `bg-slate-500/20` | `text-slate-400` | `bg-slate-500` |
| `error` | `bg-red-500/20` | `text-red-400` | `bg-red-500` |
| `status`/default | `bg-text-muted/20` | `text-text-muted` | `bg-text-muted` |

## Data Flow: Execução completa

```
1. Scanner detecta mercado → chama AgentRunner.analyze_market()
2. AgentRunner cria execution_log (status=queued)
3. ExecutionsPage polling detecta novo log → renderiza LiveExecutionCard
4. Card mostra "Waiting for agent..."
5. AgentRunner inicia execução (status=running)
6. Card detecta status=running → conecta WebSocket
7. Backend emite EXECUTION_STEP → WebSocket → Card appends step
8. TimelineProgressBar atualiza segmentos
9. ExecutionTimeline faz auto-scroll para o step
10. AgentRunner finaliza (status=completed)
11. WebSocket envia {type: "status", status: "completed"}
12. Card mostra ExecutionSummary + timeline colapsada
```

## Edge Cases
- **Execução falha antes de começar**: mostra erro no card (failure_reason)
- **Steps existentes antes do WS conectar**: carrega via REST primeiro, depois append via WS
- **WS desconecta durante streaming**: reconexão automática, carrega steps faltantes via REST
- **Múltiplas execuções simultâneas**: cada card tem seu próprio WS + hook independente
- **Execução muito longa (>1000 steps)**: buffer limita a 1000, mantendo os mais recentes
