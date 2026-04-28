"""Circuit breaker for agent runtimes."""
import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing if recovered


class CircuitBreaker:
    """Simple circuit breaker for runtime failures.

    After `failure_threshold` consecutive failures, the circuit opens for
    `recovery_timeout` seconds. After that, it enters half-open state and
    allows one test request.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 300.0,  # 5 minutes
    ):
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> CircuitState:
        return self._state

    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self._name}' entering half-open state")
                return True
            logger.debug(f"Circuit breaker '{self._name}' is OPEN — rejecting request")
            return False

        # HALF_OPEN
        return True

    def record_success(self) -> None:
        """Record a successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info(f"Circuit breaker '{self._name}' closed after recovery")
        self._failure_count = 0
        self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self._name}' OPENED after "
                f"{self._failure_count} consecutive failures"
            )


class CircuitBreakerRegistry:
    """Registry of circuit breakers, one per runtime."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, runtime_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a runtime."""
        if runtime_name not in self._breakers:
            self._breakers[runtime_name] = CircuitBreaker(name=runtime_name)
        return self._breakers[runtime_name]

    def can_execute(self, runtime_name: str) -> bool:
        return self.get(runtime_name).can_execute()

    def record_success(self, runtime_name: str) -> None:
        self.get(runtime_name).record_success()

    def record_failure(self, runtime_name: str) -> None:
        self.get(runtime_name).record_failure()
