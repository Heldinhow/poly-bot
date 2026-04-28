import asyncio
from dataclasses import dataclass, field
from typing import Callable, List
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

@dataclass
class ExecutionEvent:
    type: str
    market_id: str = ""
    question: str = ""
    message: str = ""
    data: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

# Event type constants
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
EXECUTION_STEP = "execution.step"

class ExecutionEventBus:
    def __init__(self):
        self._subscribers: List[Callable] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="event_bus")

    def publish(self, event: ExecutionEvent):
        """Synchronous publish — schedules async delivery via thread pool."""
        with self._lock:
            subscribers = list(self._subscribers)

        for sub in subscribers:
            try:
                self._executor.submit(self._deliver, sub, event)
            except Exception:
                pass

    def _deliver(self, sub: Callable, event: ExecutionEvent):
        """Deliver event to subscriber, handling both sync and async callbacks."""
        try:
            result = sub(event)
            if asyncio.iscoroutine(result):
                # Spin a mini event loop to await the coroutine
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(result)
                finally:
                    loop.close()
        except Exception:
            pass

    def subscribe(self, callback: Callable):
        with self._lock:
            self._subscribers.append(callback)
        return lambda: self._unsubscribe(callback)

    def _unsubscribe(self, callback: Callable):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)