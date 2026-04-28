# Live Execution Tracking — Plan

## Context
Copy the live execution tracking pattern from `/Users/helder/multica` into `/Users/helder/polymarket/polymarket-merge`. Today the scan runs silently in the backend; the frontend AuditPage only shows historical results after scan completes. Goal: show everything happening during execution in real-time on the AuditPage.

**Reference architecture (multica):**
- WebSocket server (`live-events-ws.ts`) for real-time event push
- Heartbeat service publishes `heartbeat.run.log`, `heartbeat.run.status`, `heartbeat.run.event`
- Client polls log chunks via HTTP and receives small chunks via WebSocket
- `LiveUpdatesProvider` manages WebSocket with exponential backoff reconnection
- `RunTranscriptView` renders normalized transcript entries

---

## Requirements Summary
- Backend pushes live execution events to frontend during scan
- Frontend displays a live transcript panel on AuditPage (expanding existing page)
- Events streamed: market fetched, filter stages, AI analysis start/end, edge calc, ACCEPT/REJECT, bet recorded, portfolio resolution
- WebSocket using multica's pattern (EventEmitter pub/sub → WebSocket server → client)

---

## Acceptance Criteria

1. During scan, frontend receives WebSocket events for each major step
2. AuditPage shows a live "Execution Transcript" panel that updates in real-time
3. Events are structured: `{ type, market_id, message, data, timestamp }`
4. Transcript shows: market name → stage → result (color-coded by outcome)
5. System handles gracefully when scan is off (idle state shown)

---

## Implementation Steps

### Phase 1: Backend — EventBus and WebSocket Server

**New file: `realtime/events.py`**

In-memory pub/sub using Python's `asyncio` EventEmitter pattern (no external deps).

```python
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Dict, List
from datetime import datetime

@dataclass
class ExecutionEvent:
    type: str           # e.g. "market.analyzed"
    market_id: str = ""
    question: str = ""
    message: str = ""
    data: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

# Event types
SCAN_STARTED = "scan.started"
MARKET_FILTERED = "market.filtered"
MARKET_ANALYZING = "market.analyzing"
MARKET_ANALYZED = "market.analyzed"
MARKET_DECIDED = "market.decided"
BET_RECORDED = "bet.recorded"
BET_ALERT_SENT = "bet.alert_sent"
PORTFOLIO_RESOLVED = "portfolio.resolved"
SCAN_COMPLETED = "scan.completed"
SCAN_ERROR = "scan.error"

class ExecutionEventBus:
    def __init__(self):
        self._subscribers: List[Callable] = []
        self._lock = asyncio.Lock()

    async def publish(self, event: ExecutionEvent):
        async with self._lock:
            for sub in self._subscribers:
                try:
                    sub(event)
                except Exception:
                    pass

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
```

**File: `api.py`** — Add WebSocket endpoint

Add route `GET /api/executions/live` using `web.WebSocketResponse`.

```python
async def executions_live_ws(self, request):
    """WebSocket endpoint for live execution events."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Build event serializer for this connection
    def send_event(event: ExecutionEvent):
        if ws.closed:
            return
        try:
            asyncio.ensure_future(ws.send_json(event.__dict__))
        except Exception:
            pass

    # Subscribe to event bus
    unsub = self._event_bus.subscribe(send_event) if self._event_bus else lambda: None

    try:
        # Send initial state
        await ws.send_json({"type": "connected", "timestamp": datetime.utcnow().isoformat() + "Z"})

        async for msg in ws:
            # Client can send ping/pong or unsubscribe messages
            if msg.type == WSMsgType.CLOSE:
                break
    finally:
        unsub()
        await ws.close()

    return ws
```

And in `create_app()`:
```python
app.router.add_get("/api/executions/live", handler.executions_live_ws)
```

**Modify `APIHandler.__init__`** to accept `event_bus`:
```python
def __init__(self, portfolio, scan_controller=None, event_bus=None):
    ...
    self._event_bus = event_bus
```

### Phase 2: Scanner — Emit events at each step

**File: `scanner.py`** — Add event emissions

Add to `Scanner.__init__`:
```python
self._event_bus = None

def set_event_bus(self, bus):
    self._event_bus = bus
```

At each step, publish events (replacing/augmenting existing `logger.info`):

```python
# Line 115: scan started
if self._event_bus:
    await self._event_bus.publish(ExecutionEvent(
        type=SCAN_STARTED,
        message="Scan started",
        data={"mode": "AGENT_RUNTIME" if self._agent_runner else "LEGACY"}
    ))

# Lines 122-128: filter stages
if self._event_bus:
    await self._event_bus.publish(ExecutionEvent(
        type=MARKET_FILTERED,
        message=f"Filters: {len(volume_filtered)}/{len(markets)} passed vol, "
                f"{len(live_filtered)}/{len(volume_filtered)} live, "
                f"{len(value_bets)}/{len(live_filtered)} value bets",
        data={"stage": "filters", "volume_filtered": len(volume_filtered),
              "live_filtered": len(live_filtered), "value_bets": len(value_bets)}
    ))

# Line 145: market analyzing
if self._event_bus:
    await self._event_bus.publish(ExecutionEvent(
        type=MARKET_ANALYZING,
        market_id=market.id,
        question=market.question,
        message=f"Analyzing: {market.question[:60]}..."
    ))

# Lines 181-189: market analyzed (AI result)
if self._event_bus and ai_probability is not None:
    await self._event_bus.publish(ExecutionEvent(
        type=MARKET_ANALYZED,
        market_id=market.id,
        question=market.question,
        message=f"AI prob={ai_probability:.0%} | implied={implied_prob:.0%} | "
                f"odds={odds:.1f}x | edge={edge:+.1%}",
        data={"ai_prob": ai_probability, "implied_prob": implied_prob,
              "odds": odds, "edge": edge, "agent": agent_name}
    ))

# Lines 214-227: decision made
if self._event_bus and decision != "SKIP":
    await self._event_bus.publish(ExecutionEvent(
        type=MARKET_DECIDED,
        market_id=market.id,
        question=market.question,
        message=f"Decision: {decision} ({reject_reason or 'edge='+str(round(edge,3))})",
        data={"decision": decision, "edge": edge, "reject_reason": reject_reason}
    ))

# Lines 243-250: bet recorded
if self._event_bus and bet:
    await self._event_bus.publish(ExecutionEvent(
        type=BET_RECORDED,
        market_id=market.id,
        question=market.question,
        message=f"Bet recorded: stake=${bet.stake:.2f} @ {odds:.1f}x odds",
        data={"stake": bet.stake, "odds": odds, "kelly_frac": bet.kelly_frac}
    ))

# Lines 329-338: portfolio resolved
if self._event_bus and stats:
    await self._event_bus.publish(ExecutionEvent(
        type=PORTFOLIO_RESOLVED,
        message=f"Portfolio: bankroll=${stats['bankroll']:.2f} | "
                f"ROI={stats['roi_pct']:.1f}% | {stats['wins']}W/{stats['losses']}L",
        data={"bankroll": stats['bankroll'], "roi_pct": stats['roi_pct'],
              "wins": stats['wins'], "losses": stats['losses'],
              "resolved": resolved}
    ))

# Line 340: scan completed
if self._event_bus:
    await self._event_bus.publish(ExecutionEvent(
        type=SCAN_COMPLETED,
        message=f"Scan complete — analyzed: {len(analyzable)}, bets: {sent}",
        data={"markets_analyzed": len(analyzable), "bets_placed": sent}
    ))
```

**Note:** Scanner.scan() is synchronous but event_bus.publish() is async. Use `asyncio.create_task()` to fire-and-forget within sync code:
```python
if self._event_bus:
    asyncio.create_task(self._event_bus.publish(event))
```

### Phase 3: Frontend — WebSocket Hook

**New file: `frontend/src/hooks/useExecutionFeed.ts`**

```typescript
import { useState, useEffect, useRef, useCallback } from 'react';

export type ExecutionEventType =
  | 'scan.started' | 'market.filtered' | 'market.analyzing'
  | 'market.analyzed' | 'market.decided' | 'bet.recorded'
  | 'bet.alert_sent' | 'portfolio.resolved' | 'scan.completed'
  | 'scan.error' | 'connected';

export interface ExecutionEvent {
  type: ExecutionEventType;
  market_id?: string;
  question?: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

type ScanStatus = 'idle' | 'running' | 'error';

const MAX_EVENTS = 500;
const BASE_DELAY = 1000;
const MAX_DELAY = 15000;

export function useExecutionFeed(wsUrl = '/api/executions/live') {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelayRef = useRef(BASE_DELAY);
  const retryTimerRef = useRef<number | null>(null);
  const isUnmountedRef = useRef(false);

  const addEvent = useCallback((event: ExecutionEvent) => {
    setEvents(prev => {
      const next = [...prev, event];
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
    });

    // Update scan status based on event type
    if (event.type === 'scan.started') setScanStatus('running');
    else if (event.type === 'scan.completed' || event.type === 'scan.error') {
      // Keep status for 3s then revert to idle
      setTimeout(() => { if (!isUnmountedRef.current) setScanStatus('idle'); }, 3000);
    }
  }, []);

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryDelayRef.current = BASE_DELAY;
      };

      ws.onmessage = (evt) => {
        try {
          const event = JSON.parse(evt.data) as ExecutionEvent;
          addEvent(event);
        } catch { /* ignore parse errors */ }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Exponential backoff reconnect
        if (!isUnmountedRef.current) {
          retryTimerRef.current = window.setTimeout(() => {
            retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_DELAY);
            connect();
          }, retryDelayRef.current);
        }
      };
    } catch {
      // Connection failed, retry
      if (!isUnmountedRef.current) {
        retryTimerRef.current = window.setTimeout(connect, retryDelayRef.current);
      }
    }
  }, [wsUrl, addEvent]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();
    return () => {
      isUnmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, isConnected, scanStatus };
}
```

### Phase 4: Frontend — Live Transcript Component

**New file: `frontend/src/components/ExecutionFeed.tsx`**

```typescript
import { useExecutionFeed, ExecutionEvent } from '@/hooks/useExecutionFeed';
import { useEffect, useRef } from 'react';

const EVENT_COLORS: Record<string, string> = {
  'scan.started': 'text-amber-400',
  'market.filtered': 'text-slate-400',
  'market.analyzing': 'text-amber-400',
  'market.analyzed': 'text-cyan-400',
  'market.decided': 'text-blue-400',
  'bet.recorded': 'text-green-400',
  'bet.alert_sent': 'text-green-500',
  'portfolio.resolved': 'text-slate-300',
  'scan.completed': 'text-emerald-400',
  'scan.error': 'text-rose-400',
};

function EventEntry({ event }: { event: ExecutionEvent }) {
  const color = EVENT_COLORS[event.type] || 'text-slate-500';
  return (
    <div className={`text-xs font-mono ${color} py-0.5`}>
      <span className="text-slate-600 mr-2">{event.timestamp.split('T')[1]?.slice(0, 8)}</span>
      <span>[{event.type}]</span>
      <span className="ml-2">{event.message}</span>
    </div>
  );
}

export default function ExecutionFeed() {
  const { events, isConnected, scanStatus } = useExecutionFeed();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-sm font-medium text-text-primary">
            {scanStatus === 'running' ? 'Scan Running' :
             scanStatus === 'error' ? 'Scan Error' : 'Scan Idle'}
          </span>
        </div>
        {events.length > 0 && (
          <span className="text-xs text-text-muted">{events.length} events</span>
        )}
      </div>

      {events.length === 0 ? (
        <p className="text-sm text-text-muted italic">
          {isConnected ? 'Waiting for scan to start...' : 'Connecting to live feed...'}
        </p>
      ) : (
        <div className="max-h-64 overflow-y-auto space-y-0.5 bg-black/20 rounded p-2">
          {events.map((event, i) => (
            <EventEntry key={i} event={event} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
```

### Phase 5: Integrate into AuditPage

**File: `frontend/src/pages/AuditPage.tsx`**

Add import and render `ExecutionFeed` at top:

```typescript
import ExecutionFeed from '@/components/ExecutionFeed';

// In JSX, before <AuditFilterBar />:
<ExecutionFeed />
```

### Phase 6: Wire event bus in main.py

**File: `main.py`**

```python
from realtime.events import ExecutionEventBus

def main():
    ...
    event_bus = ExecutionEventBus()
    scanner = Scanner(...)
    scanner.set_event_bus(event_bus)
    api_handler = APIHandler(portfolio, scan_controller=scan_controller, event_bus=event_bus)
    ...

    start_api_server(portfolio, port=8080, scan_controller=scan_controller)
    # Attach event_bus to the API handler after server starts
    # (done via passing to create_app which passes to APIHandler constructor)
```

Note: Since both scanner and API run in the same process via the main.py loop, the in-memory event bus works without any external dependency.

---

## File Inventory

| File | Action |
|------|--------|
| `realtime/events.py` | **NEW** — ExecutionEventBus with pub/sub |
| `api.py` | **MODIFY** — add WebSocket route + `event_bus` param to APIHandler |
| `scanner.py` | **MODIFY** — add `set_event_bus()` + emit events at each step |
| `main.py` | **MODIFY** — create event bus, pass to Scanner + APIHandler |
| `frontend/src/hooks/useExecutionFeed.ts` | **NEW** — WebSocket hook |
| `frontend/src/components/ExecutionFeed.tsx` | **NEW** — live transcript UI |
| `frontend/src/pages/AuditPage.tsx` | **MODIFY** — import and render ExecutionFeed |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Scanner.scan() is sync but event_bus.publish is async | Use `asyncio.create_task()` to fire-and-forget without blocking scan loop |
| WS reconnect flood on unstable connections | Exponential backoff: 1s → 2s → 4s → ... → max 15s with jitter |
| Large event volume during scan | Cap at 500 events in frontend memory, drop oldest |
| Both scanner and API run in main.py same process | In-memory event bus works fine; no Redis needed |
| Frontend reconnects mid-scan and misses events | Events are fire-and-forget; frontend reconnects and shows from that point forward (acceptable — no replay needed) |

---

## Verification Steps

1. **Backend startup**: `python main.py` — no errors, log shows "Scanner initialized [AGENT RUNTIME MODE]"
2. **WebSocket endpoint**: Visit `ws://localhost:8080/api/executions/live` — receives `{"type": "connected", ...}` JSON
3. **Trigger scan**: `curl -X POST http://localhost:8080/api/scan/enable`
4. **Watch events**: Frontend AuditPage shows live events appearing in ExecutionFeed panel
5. **Event sequence**: Each market shows: question → analysis → decision → bet (if ACCEPT)
6. **End state**: scan.completed event shows summary with bankroll/ROI
7. **Idle state**: When scan done, panel shows "Scan Idle" with green dot
8. **Reconnect test**: Refresh page while scan running — WS reconnects automatically

---

## ADR — Decision: WebSocket over SSE

**Decision**: Use WebSocket (not SSE) for live execution tracking.

**Drivers**:
- multica uses WebSocket — proven pattern to follow
- WebSocket supports bidirectional communication (client can send ping/pong/commands)
- Easier to manage reconnection as a client-side concern

**Alternatives considered**:
- SSE: simpler server-side but no native reconnection support; less proven in this codebase
- Polling: high latency, wastes bandwidth

**Why chosen**: Matches multica's proven architecture; WebSocket support already available in aiohttp.

**Consequences**:
- aiohttp `web.WebSocketResponse` replaces current pure REST for live feed
- Frontend needs `useEffect` cleanup to avoid memory leaks on unmount

**Follow-ups**:
- If scaling to multiple backend processes later → replace in-memory bus with Redis pub/sub
- If needing authenticated WS → add token validation in `executions_live_ws` handler