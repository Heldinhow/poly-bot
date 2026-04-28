"""Backend registry — factory for agent runtime backends."""
import logging
from typing import Type

from agents.runtime.models import AgentBackend

logger = logging.getLogger(__name__)


class BackendRegistry:
    """Factory registry for agent backends. Register once, instantiate on demand."""

    def __init__(self):
        self._backends: dict[str, type[AgentBackend]] = {}

    def register(self, name: str, backend_class: type[AgentBackend]) -> None:
        """Register a backend class under a runtime name."""
        self._backends[name] = backend_class
        logger.debug(f"Backend registered: {name}")

    def get(self, name: str) -> AgentBackend | None:
        """Instantiate and return a backend by name."""
        backend_class = self._backends.get(name)
        if not backend_class:
            logger.warning(f"Backend not registered: {name}")
            return None
        try:
            return backend_class()
        except Exception as e:
            logger.error(f"Failed to instantiate backend {name}: {e}")
            return None

    def list_registered(self) -> list[str]:
        """Return list of registered backend names."""
        return list(self._backends.keys())
