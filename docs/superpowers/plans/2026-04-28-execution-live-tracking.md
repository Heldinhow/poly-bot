# Execution Live Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static ExecutionCards on the ExecutionsPage with LiveExecutionCards that stream agent steps in real-time via WebSocket, show a colored timeline progress bar, and display a clean output summary when complete.

**Architecture:** Backend broadcasts each agent step via the existing EventBus after DB persistence. A new per-execution WebSocket endpoint (`/api/executions/{id}/stream`) filters and forwards steps. Frontend uses a `useExecutionStream` hook that loads existing steps via REST then appends via WS, powering `LiveExecutionCard` with `TimelineProgressBar`, `ExecutionTimeline`, and `ExecutionSummary` sub-components.

**Tech Stack:** Python 3.14 (aiohttp WebSocket, EventBus), React 19 + TypeScript (WebSocket API, TanStack Query), Tailwind CSS v4 (design tokens from globals.css)

---

### Task 1: Add EXECUTION_STEP event type

**Files:**
- Modify: `realtime/events.py:20-31`

- [ ] **Step 1: Add the new event type constant**

At `realtime/events.py` line 31 (after `SCAN_ERROR`), add:

```python
EXECUTION_STEP = "execution.step"
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import realtime.events; print(realtime.events.EXECUTION_STEP)"`
Expected: `execution.step`

- [ ] **Step 3: Commit**

```bash
git add realtime/events.py
git commit -m "feat: add EXECUTION_STEP event type for live step streaming"
```

---

### Task 2: Broadcast steps via EventBus in ExecutionTracker

**Files:**
- Modify: `agents/tracker.py:1-136`

- [ ] **Step 1: Add event_bus to constructor**

Replace the `__init__` method (lines 16-19) with:

```python
def __init__(self, repository: ExecutionRepository | None = None, event_bus=None):
    self._repo = repository or ExecutionRepository()
    self._truth_repo = TruthClaimRepository()
    self._extractor = TruthClaimExtractor()
    self._event_bus = event_bus
```

- [ ] **Step 2: Add import for ExecutionEvent**

Add after the existing imports at line 6:

```python
from realtime.events import EXECUTION_STEP, ExecutionEvent
```

- [ ] **Step 3: Add _broadcast_step method**

Add this method after `_save_step` (after line 91):

```python
def _broadcast_step(self, log_id: UUID, seq: int, msg: Message) -> None:
    if self._event_bus is None:
        return
    try:
        event = ExecutionEvent(
            type=EXECUTION_STEP,
            data={
                "execution_log_id": str(log_id),
                "seq": seq,
                "step_type": msg.type.value,
                "content": msg.content if msg.type != MessageType.TOOL_RESULT else None,
                "tool_name": msg.metadata.get("tool_name") if msg.metadata else None,
                "tool_input": msg.metadata.get("input") if msg.metadata else None,
                "tool_output": msg.content if msg.type == MessageType.TOOL_RESULT else None,
            },
        )
        self._event_bus.publish(event)
    except Exception:
        pass
```

- [ ] **Step 4: Call _broadcast_step from _save_step**

In the `_save_step` method, after the `self._repo.create_step(...)` call (after line 91), add:

```python
self._broadcast_step(log_id, seq, msg)
```

- [ ] **Step 5: Verify syntax**

Run: `python -c "from agents.tracker import ExecutionTracker; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add agents/tracker.py
git commit -m "feat: broadcast execution steps via EventBus for live streaming"
```

---

### Task 3: Wire event_bus through AgentRunner to ExecutionTracker

**Files:**
- Modify: `agents/runtime/runner.py:28-40`

- [ ] **Step 1: Add event_bus parameter to AgentRunner**

Replace the `__init__` signature (lines 28-35) with:

```python
def __init__(
    self,
    registry: AgentRegistry | None = None,
    runtime_manager: RuntimeManager | None = None,
    tracker: ExecutionTracker | None = None,
    exec_env: ExecutionEnvironment | None = None,
    circuit_breakers: CircuitBreakerRegistry | None = None,
    event_bus=None,
):
    self._registry = registry or AgentRegistry()
    self._runtime = runtime_manager or RuntimeManager()
    self._tracker = tracker or ExecutionTracker(event_bus=event_bus)
    self._exec_env = exec_env or ExecutionEnvironment()
    self._circuit_breakers = circuit_breakers or CircuitBreakerRegistry()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "from agents.runtime.runner import AgentRunner; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agents/runtime/runner.py
git commit -m "feat: wire EventBus through AgentRunner to ExecutionTracker"
```

---

### Task 4: Wire event_bus in main.py

**Files:**
- Modify: `main.py:82-83`

- [ ] **Step 1: Pass event_bus to AgentRunner**

Replace line 83 with:

```python
agent_runner = AgentRunner(event_bus=event_bus)
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import main; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: pass EventBus to AgentRunner for step streaming"
```

---

### Task 5: Add per-execution WebSocket streaming endpoint

**Files:**
- Modify: `api.py:574-609`

- [ ] **Step 1: Add the new WebSocket handler**

After the `executions_live_ws` method (after line 609), add:

```python
async def executions_stream_ws(self, request):
    """GET /api/executions/{id}/stream — WebSocket endpoint streaming steps for one execution."""
    log_id_str = request.match_info["id"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Send initial connection confirmation
    await ws.send_json({"type": "connected", "execution_log_id": log_id_str})

    sent_seqs = set()
    subscription = None

    def on_event(data):
        if data.type == EXECUTION_STEP:
            exec_data = data.data if isinstance(data.data, dict) else {}
            if exec_data.get("execution_log_id") != log_id_str:
                return
            seq = exec_data.get("seq")
            if seq in sent_seqs:
                return
            sent_seqs.add(seq)
            asyncio.create_task(ws.send_json({
                "type": "step",
                "seq": exec_data.get("seq"),
                "step_type": exec_data.get("step_type"),
                "content": exec_data.get("content"),
                "tool_name": exec_data.get("tool_name"),
                "tool_input": exec_data.get("tool_input"),
                "tool_output": exec_data.get("tool_output"),
            }))

    if self._event_bus:
        subscription = self._event_bus.subscribe(on_event)

    # Heartbeat every 15s
    async def heartbeat():
        while not ws.closed:
            try:
                await ws.send_json({"type": "ping"})
                await asyncio.sleep(15)
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.CLOSE:
                break
            elif msg.type == web.WSMsgType.ERROR:
                break
    finally:
        heartbeat_task.cancel()
        if subscription is not None:
            self._event_bus.unsubscribe(subscription)
        await ws.close()
```

- [ ] **Step 2: Add import for EXECUTION_STEP at top of api.py**

After line 20 (the `from models.bet import Bet` line), add:

```python
from realtime.events import EXECUTION_STEP
```

- [ ] **Step 3: Register the route**

After line 793 (`app.router.add_get("/api/executions/live", ...)`), add:

```python
app.router.add_get("/api/executions/{id}/stream", handler.executions_stream_ws)
```

- [ ] **Step 4: Move this route BEFORE the `/api/executions/{id}` catch-all**

The route `/api/executions/{id}/stream` must be registered before `/api/executions/{id}` to avoid the `{id}` param capturing "stream". Replace lines 790-793:

```python
app.router.add_get("/api/executions", handler.list_executions)
app.router.add_get("/api/executions/live", handler.executions_live_ws)
app.router.add_get("/api/executions/{id}/stream", handler.executions_stream_ws)
app.router.add_get("/api/executions/{id}/steps", handler.get_execution_steps)
app.router.add_get("/api/executions/{id}", handler.get_execution)
```

- [ ] **Step 5: Verify syntax**

Run: `python -c "import api; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add api.py
git commit -m "feat: add per-execution WebSocket endpoint for step streaming"
```

---

### Task 6: Create useExecutionStream hook

**Files:**
- Create: `frontend/src/hooks/useExecutionStream.ts`

- [ ] **Step 1: Write the hook**

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8080';
const MAX_STEPS = 1000;
const BASE_DELAY = 1000;
const MAX_DELAY = 15000;

export interface StreamStep {
  seq: number;
  step_type: string;
  content: string | null;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: string | null;
}

export interface ExecutionStep {
  id: string;
  seq: number;
  step_type: string;
  content: string | null;
  tool_name: string | null;
  tool_input: unknown;
  tool_output: string | null;
  duration_ms: number | null;
}

export function useExecutionStream(executionId: string | null) {
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelayRef = useRef(BASE_DELAY);
  const retryTimerRef = useRef<number | null>(null);
  const isUnmountedRef = useRef(false);
  const seenSeqsRef = useRef(new Set<number>());

  const connect = useCallback(() => {
    if (!executionId || isUnmountedRef.current) return;

    try {
      const wsUrl = `${API_BASE}/api/executions/${executionId}/stream`.replace('http://', 'ws://');
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryDelayRef.current = BASE_DELAY;
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'step') {
            const step: StreamStep = msg;
            if (!seenSeqsRef.current.has(step.seq)) {
              seenSeqsRef.current.add(step.seq);
              setSteps(prev => {
                const next = [
                  ...prev,
                  {
                    id: `${executionId}-${step.seq}`,
                    seq: step.seq,
                    step_type: step.step_type,
                    content: step.content,
                    tool_name: step.tool_name,
                    tool_input: step.tool_input,
                    tool_output: step.tool_output,
                    duration_ms: null,
                  } as ExecutionStep,
                ];
                return next.length > MAX_STEPS ? next.slice(-MAX_STEPS) : next;
              });
            }
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        if (!isUnmountedRef.current) {
          retryTimerRef.current = window.setTimeout(() => {
            retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_DELAY);
            connect();
          }, retryDelayRef.current);
        }
      };
    } catch {
      if (!isUnmountedRef.current) {
        retryTimerRef.current = window.setTimeout(connect, retryDelayRef.current);
      }
    }
  }, [executionId]);

  // Load initial steps from REST then connect WS
  useEffect(() => {
    if (!executionId) {
      setSteps([]);
      return;
    }

    isUnmountedRef.current = false;
    seenSeqsRef.current = new Set();

    // Load existing steps via REST first
    fetch(`${API_BASE}/api/executions/${executionId}/steps`)
      .then(res => res.json())
      .then((data: ExecutionStep[]) => {
        if (!isUnmountedRef.current && Array.isArray(data)) {
          data.forEach(s => seenSeqsRef.current.add(s.seq));
          setSteps(data);
        }
        connect();
      })
      .catch(() => {
        connect();
      });

    return () => {
      isUnmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [executionId, connect]);

  return { steps, isConnected };
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit --pretty src/hooks/useExecutionStream.ts`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useExecutionStream.ts
git commit -m "feat: add useExecutionStream hook for real-time step streaming"
```

---

### Task 7: Create TimelineProgressBar component

**Files:**
- Create: `frontend/src/components/TimelineProgressBar.tsx`

- [ ] **Step 1: Write the component**

```tsx
import type { ExecutionStep } from '@/hooks/useExecutions';

const stepColors: Record<string, string> = {
  text: 'bg-emerald-500',
  thinking: 'bg-violet-500',
  tool_use: 'bg-blue-500',
  tool_result: 'bg-slate-500',
  error: 'bg-red-500',
};

const stepLabels: Record<string, string> = {
  text: 'Text',
  thinking: 'Thinking',
  tool_use: 'Tool Use',
  tool_result: 'Tool Result',
  error: 'Error',
};

interface Props {
  steps: ExecutionStep[];
}

export default function TimelineProgressBar({ steps }: Props) {
  if (steps.length === 0) return null;

  const counts: Record<string, number> = {};
  for (const s of steps) {
    counts[s.step_type] = (counts[s.step_type] || 0) + 1;
  }

  const total = steps.length;

  return (
    <div className="flex h-1 rounded-full overflow-hidden gap-px">
      {Object.entries(counts).map(([type, count]) => (
        <div
          key={type}
          className={`${stepColors[type] || 'bg-text-muted'} transition-all duration-200`}
          style={{ width: `${(count / total) * 100}%` }}
          title={`${stepLabels[type] || type}: ${count} steps`}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit --pretty src/components/TimelineProgressBar.tsx`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TimelineProgressBar.tsx
git commit -m "feat: add TimelineProgressBar component with colored segments"
```

---

### Task 8: Create ExecutionTimeline component

**Files:**
- Create: `frontend/src/components/ExecutionTimeline.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, ChevronRight, Brain, Wrench, AlertCircle, ArrowDown } from 'lucide-react';
import type { ExecutionStep } from '@/hooks/useExecutions';

const stepBadgeColors: Record<string, string> = {
  text: 'bg-emerald-500/20 text-emerald-400',
  thinking: 'bg-violet-500/20 text-violet-400',
  tool_use: 'bg-blue-500/20 text-blue-400',
  tool_result: 'bg-slate-500/20 text-slate-400',
  error: 'bg-red-500/20 text-red-400',
};

const stepIcons: Record<string, React.ReactNode> = {
  thinking: <Brain className="h-3 w-3" />,
  tool_use: <Wrench className="h-3 w-3" />,
  error: <AlertCircle className="h-3 w-3" />,
};

function StepRow({ step }: { step: ExecutionStep }) {
  const [expanded, setExpanded] = useState(false);
  const type = step.step_type;

  const summary = type === 'tool_use'
    ? `${step.tool_name || 'tool'}: ${JSON.stringify(step.tool_input || {}).slice(0, 60)}`
    : type === 'tool_result'
    ? (step.tool_output || '').slice(0, 80)
    : (step.content || '').slice(0, 150);

  const hasDetail = (step.content && step.content.length > 150)
    || (step.tool_output && step.tool_output.length > 80)
    || (step.tool_input && JSON.stringify(step.tool_input).length > 60);

  return (
    <div className="py-1.5">
      <button
        onClick={() => hasDetail && setExpanded(!expanded)}
        className="flex w-full items-start gap-2 text-left group"
      >
        <span className="shrink-0 text-[10px] text-text-muted/50 font-mono mt-0.5">
          #{step.seq}
        </span>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${stepBadgeColors[type] || 'bg-text-muted/20 text-text-muted'}`}>
          {stepIcons[type] && <span className="mr-1 inline-block align-middle">{stepIcons[type]}</span>}
          {type === 'tool_use' ? step.tool_name || 'tool' : type === 'tool_result' ? 'result' : type}
        </span>
        <span className={`min-w-0 flex-1 text-xs truncate ${
          type === 'thinking' ? 'italic text-violet-300/60' :
          type === 'error' ? 'text-red-400' :
          'text-text-secondary'
        }`}>
          {summary || '\u00A0'}
        </span>
        {hasDetail && (
          <span className="shrink-0 text-text-muted/40 group-hover:text-text-muted">
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </span>
        )}
      </button>
      {expanded && (
        <div className="mt-1 ml-8 rounded-lg bg-surface-hover/50 p-2.5">
          {step.content && (
            <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono">{step.content}</pre>
          )}
          {step.tool_input && (
            <pre className="text-xs text-text-muted whitespace-pre-wrap font-mono mt-1">
              {JSON.stringify(step.tool_input, null, 2)}
            </pre>
          )}
          {step.tool_output && (
            <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono mt-1 max-h-48 overflow-auto">
              {step.tool_output.length > 4000 ? step.tool_output.slice(0, 4000) + '\n... [truncated]' : step.tool_output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  steps: ExecutionStep[];
}

export default function ExecutionTimeline({ steps }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const prevLengthRef = useRef(steps.length);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      setUserScrolledUp(false);
    }
  }, []);

  useEffect(() => {
    if (steps.length > prevLengthRef.current) {
      prevLengthRef.current = steps.length;
      if (!userScrolledUp) {
        scrollToBottom();
      }
    }
  }, [steps.length, userScrolledUp, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distFromBottom > 40) {
      setUserScrolledUp(true);
    } else {
      setUserScrolledUp(false);
    }
  }, []);

  if (steps.length === 0) {
    return <p className="text-xs text-text-muted py-4 text-center">Waiting for agent...</p>;
  }

  return (
    <div className="relative">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="max-h-72 overflow-y-auto"
      >
        {steps.map(step => (
          <StepRow key={`${step.seq}-${step.step_type}`} step={step} />
        ))}
      </div>
      {userScrolledUp && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-full bg-accent-cyan/20 border border-accent-cyan/30 px-3 py-1 text-xs text-accent-cyan hover:bg-accent-cyan/30 transition-colors"
        >
          <ArrowDown className="h-3 w-3" />
          Latest
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit --pretty src/components/ExecutionTimeline.tsx`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ExecutionTimeline.tsx
git commit -m "feat: add ExecutionTimeline component with auto-scroll"
```

---

### Task 9: Create ExecutionSummary component

**Files:**
- Create: `frontend/src/components/ExecutionSummary.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { Copy, FileText } from 'lucide-react';
import type { Execution } from '@/hooks/useExecutions';

const decisionColors: Record<string, string> = {
  ACCEPT: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  REJECT: 'bg-red-500/20 text-red-400 border-red-500/30',
  SKIP: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

interface Props {
  exec: Execution;
}

export default function ExecutionSummary({ exec }: Props) {
  const prob = exec.probability;
  const conf = exec.confidence;

  return (
    <div className="space-y-3 animate-fade-up">
      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-2">
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Probability</p>
          <p className="mt-0.5 text-sm font-mono text-emerald-400">
            {prob !== null ? `${(prob * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Confidence</p>
          <p className="mt-0.5 text-sm font-mono text-blue-400">
            {conf !== null ? `${(conf * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Duration</p>
          <p className="mt-0.5 text-sm font-mono text-amber-400">
            {exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Tokens</p>
          <p className="mt-0.5 text-sm font-mono text-text-secondary">
            {exec.input_tokens > 0 ? `${exec.input_tokens}+${exec.output_tokens}` : '—'}
          </p>
        </div>
      </div>

      {/* Reasoning */}
      {exec.reasoning && (
        <div className="rounded-lg bg-bg-deep p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="h-3 w-3 text-text-muted" />
            <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Reasoning</span>
          </div>
          <p className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
            {exec.reasoning}
          </p>
        </div>
      )}

      {/* Error */}
      {exec.status === 'failed' && exec.error_message && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
          <p className="text-xs text-red-400">{exec.error_message}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => {
            if (exec.reasoning) {
              navigator.clipboard.writeText(exec.reasoning);
            }
          }}
          className="flex items-center gap-1 rounded-lg border border-border-subtle px-2.5 py-1.5 text-[10px] text-text-muted hover:text-text-primary hover:border-border-medium transition-colors"
        >
          <Copy className="h-3 w-3" />
          Copy reasoning
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit --pretty src/components/ExecutionSummary.tsx`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ExecutionSummary.tsx
git commit -m "feat: add ExecutionSummary component for completed executions"
```

---

### Task 10: Create LiveExecutionCard component

**Files:**
- Create: `frontend/src/components/LiveExecutionCard.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Clock, Loader2 } from 'lucide-react';
import { useExecutionStream } from '@/hooks/useExecutionStream';
import type { Execution } from '@/hooks/useExecutions';
import TimelineProgressBar from '@/components/TimelineProgressBar';
import ExecutionTimeline from '@/components/ExecutionTimeline';
import ExecutionSummary from '@/components/ExecutionSummary';

const statusColors: Record<string, string> = {
  queued: 'bg-text-muted/20 text-text-muted',
  claimed: 'bg-accent-cyan/20 text-accent-cyan',
  running: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-emerald-500/20 text-emerald-400',
  failed: 'bg-rose-500/20 text-rose-400',
  cancelled: 'bg-text-muted/20 text-text-muted',
};

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}m ${sec}s`;
}

interface Props {
  exec: Execution;
}

export default function LiveExecutionCard({ exec }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isRunning = exec.status === 'running';
  const isCompleted = exec.status === 'completed' || exec.status === 'failed';

  // Stream steps when running
  const { steps, isConnected } = useExecutionStream(isRunning || isCompleted ? exec.id : null);

  // Live elapsed time for running executions
  const [elapsed, setElapsed] = useState(exec.duration_ms || 0);
  useEffect(() => {
    if (!isRunning || !exec.started_at) return;
    const start = new Date(exec.started_at!).getTime();
    const interval = setInterval(() => {
      setElapsed(Date.now() - start);
    }, 1000);
    return () => clearInterval(interval);
  }, [isRunning, exec.started_at]);

  const toolCount = steps.filter(s => s.step_type === 'tool_use').length;

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex w-full items-center justify-between p-4 text-left transition-colors ${
          isRunning ? 'bg-amber-500/5 hover:bg-amber-500/10' : 'hover:bg-surface-hover/50'
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          {/* Status badge */}
          <span className={`shrink-0 flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[exec.status] || 'bg-text-muted/20 text-text-muted'}`}>
            {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            {exec.status}
            {isConnected && isRunning && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            )}
          </span>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {exec.agent_name && (
                <span className="text-xs font-medium text-accent-cyan truncate max-w-[120px]">
                  {exec.agent_name}
                </span>
              )}
              <span className="text-xs text-text-muted">
                {exec.runtime}{exec.model ? ` · ${exec.model}` : ''}
                {isRunning && elapsed > 0 && (
                  <span className="ml-2">· {formatElapsed(elapsed)}</span>
                )}
                {toolCount > 0 && (
                  <span className="ml-2">· {toolCount} tools</span>
                )}
              </span>
            </div>
            <p className="text-sm text-text-primary truncate max-w-[400px] mt-0.5">
              {exec.task_id?.slice(0, 8) || exec.id?.slice(0, 8)} — {exec.market_id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 shrink-0 ml-4">
          {exec.duration_ms && !isRunning && (
            <span className="hidden sm:flex items-center gap-1 text-xs text-text-muted">
              <Clock className="h-3 w-3" />
              {formatElapsed(exec.duration_ms)}
            </span>
          )}
          {exec.probability !== null && !isRunning && (
            <span className="text-sm font-mono text-text-secondary">
              P={(exec.probability * 100).toFixed(0)}% C={exec.confidence?.toFixed(2) || '?'}
            </span>
          )}
          {expanded ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-border-subtle px-4 pb-4 pt-3 space-y-4">
          {/* Only show timeline for running or completed */}
          {(isRunning || isCompleted) && (
            <>
              <TimelineProgressBar steps={steps} />
              <ExecutionTimeline steps={steps} />
            </>
          )}

          {/* Queued / claimed state */}
          {!isRunning && !isCompleted && (
            <div className="py-8 text-center">
              <Loader2 className="h-5 w-5 animate-spin text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-muted">Waiting for agent...</p>
            </div>
          )}

          {/* Summary for completed */}
          {isCompleted && <ExecutionSummary exec={exec} />}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd frontend && npx tsc --noEmit --pretty src/components/LiveExecutionCard.tsx`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LiveExecutionCard.tsx
git commit -m "feat: add LiveExecutionCard with real-time streaming and output summary"
```

---

### Task 11: Update ExecutionsPage to use LiveExecutionCard

**Files:**
- Modify: `frontend/src/pages/ExecutionsPage.tsx`
- Modify: `frontend/src/hooks/useExecutions.ts`

- [ ] **Step 1: Add agent_name to Execution type in useExecutions.ts**

In `frontend/src/hooks/useExecutions.ts`, add `agent_name` to the `Execution` interface (after line 8):

```typescript
export interface Execution {
  id: string;
  task_id: string;
  market_id: string;
  agent_id: string;
  agent_name?: string;
  runtime: string;
  model: string | null;
  status: string;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  probability: number | null;
  confidence: number | null;
  reasoning: string | null;
  error_message: string | null;
  failure_reason: string | null;
  input_tokens: number;
  output_tokens: number;
}
```

- [ ] **Step 2: Replace ExecutionsPage content**

Replace `frontend/src/pages/ExecutionsPage.tsx` completely:

```tsx
import { useExecutions } from '@/hooks/useExecutions';
import { Activity } from 'lucide-react';
import LiveExecutionCard from '@/components/LiveExecutionCard';

export default function ExecutionsPage() {
  const { executions, isLoading } = useExecutions();

  if (isLoading) return <div className="p-8 text-text-muted">Loading executions...</div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2">
        <Activity className="h-6 w-6 text-accent-cyan" />
        <h2 className="text-2xl font-bold text-text-primary">Executions</h2>
        {executions && (
          <span className="ml-2 text-sm text-text-muted">({executions.length})</span>
        )}
      </div>

      <div className="space-y-3">
        {executions?.map(exec => (
          <LiveExecutionCard key={exec.id} exec={exec} />
        ))}
        {(!executions || executions.length === 0) && (
          <p className="text-sm text-text-muted">No executions yet.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript across all new files**

Run: `cd frontend && npx tsc --noEmit --pretty`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ExecutionsPage.tsx frontend/src/hooks/useExecutions.ts
git commit -m "feat: replace ExecutionCard with LiveExecutionCard on ExecutionsPage"
```

---

### Task 12: Integration test — verify end-to-end flow

- [ ] **Step 1: Start the backend**

```bash
PYTHONPATH=. python -c "
from realtime.events import ExecutionEventBus, EXECUTION_STEP, ExecutionEvent
bus = ExecutionEventBus()
event = ExecutionEvent(type=EXECUTION_STEP, data={'execution_log_id': 'test-123', 'seq': 1, 'step_type': 'thinking', 'content': 'test thought'})
bus.publish(event)
print('Event published OK')
"
```
Expected: `Event published OK`

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```
Expected: Build succeeds with no errors

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```

---

## Verification Checklist

After all tasks are complete, verify by:
1. **Start full app**: `PYTHONPATH=. python main.py`
2. **Open dashboard** at `http://localhost:8080`
3. **Navigate to Executions tab**
4. **Trigger a scan** (or wait for next cycle)
5. **Observe**: Running executions show live timeline with colored steps, auto-scroll, and elapsed time
6. **Observe**: Completed executions show output summary with probability, confidence, edge, and reasoning
7. **Observe**: Timeline progress bar shows correct colored segments proportional to step type counts
