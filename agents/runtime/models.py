"""Core dataclasses for the agent runtime."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
    sources: list[str] = field(default_factory=list)
    raw_output: str = ""
    error_message: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ExecOptions:
    cwd: str
    model: str = ""
    system_prompt: str = ""
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=20))
    max_retries: int = 1
    resume_session_id: str | None = None
    custom_args: list[str] = field(default_factory=list)
    custom_env: dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    task_id: str
    market_id: str
    agent_id: str
    workspace_id: str


@dataclass
class Task:
    """A task dispatched by the scanner to the runtime."""
    task_id: str
    market_id: str
    question: str
    yes_price: float
    no_price: float
    volume_24h: float
    resolution_date: str | None = None
    agent_id: str = ""
    agent_config: dict[str, Any] = field(default_factory=dict)


class Session:
    """A session represents an ongoing agent execution."""

    def __init__(self):
        self.messages: AsyncIterator[Message] | None = None
        self.result: asyncio.Future[Result] = asyncio.Future()


class AgentBackend(ABC):
    """Abstract base class for all agent runtime backends."""

    @abstractmethod
    async def execute(
        self,
        ctx: ExecutionContext,
        prompt: str,
        opts: ExecOptions,
    ) -> Session:
        """Spawn the agent CLI and return a session with streaming messages."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the CLI for this backend is installed and accessible."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this backend."""
        raise NotImplementedError
