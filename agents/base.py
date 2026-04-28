"""Base agent class for all agents."""
from abc import ABC
from dataclasses import dataclass
from typing import Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: str
    model: str = "MiniMax"
    temperature: float = 0.7
    max_tokens: int = 2048


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        name: str,
        role: str,
        model: str = "MiniMax",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.config = AgentConfig(
            name=name,
            role=role,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.name = name
        self.role = role
        self._llm_client: Any = None

    @property
    def prompt(self) -> str:
        """Get the agent's system prompt."""
        return f"You are {self.name}, {self.role}."

    async def think(self, input_text: str) -> str:
        """Process input and return agent's response."""
        from llm import MinimaxClient

        if self._llm_client is None:
            self._llm_client = MinimaxClient()

        try:
            return await self._llm_client.complete(
                prompt=input_text,
                system=self.prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception as e:
            logger.error(f"{self.name} think() failed: {e}")
            raise

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze context and return analysis result."""
        raise NotImplementedError("Subclasses must implement analyze")
