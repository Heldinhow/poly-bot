"""Execution tracker — consumes agent message streams and persists to DB."""
import logging
from uuid import UUID

from agents.runtime.models import Message, MessageType, Result, Session
from db.execution_repository import ExecutionRepository

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """Consumes agent message streams and persists steps to the database in real-time."""

    def __init__(self, repository: ExecutionRepository | None = None):
        self._repo = repository or ExecutionRepository()

    def claim(self, log_id: UUID, runtime: str) -> bool:
        """Claim an execution log for a specific runtime.

        Returns True if successfully claimed, False if already claimed by another runtime.
        This prevents race conditions when multiple runtimes try to execute the same task.
        """
        success = self._repo.claim_log(log_id, runtime)
        if success:
            logger.info(f"Execution log claimed: id={log_id}, runtime={runtime}")
        else:
            logger.warning(f"Failed to claim execution log: id={log_id} (already claimed)")
        return success

    def start(self, log_id: UUID) -> bool:
        """Mark an execution log as running."""
        success = self._repo.start_log(log_id)
        if success:
            logger.info(f"Execution log started: id={log_id}")
        return success

    async def track(self, log_id: UUID, session: Session) -> None:
        """Consume the message stream and persist each message as a step.

        Args:
            log_id: UUID of the execution_logs row.
            session: Session with an async message iterator.
        """
        seq = 0
        try:
            async for msg in session.messages:
                seq += 1
                await self._save_step(log_id, seq, msg)
        except Exception as e:
            logger.error(f"Error tracking execution {log_id}: {e}")
            seq += 1
            await self._save_step(
                log_id,
                seq,
                Message(type=MessageType.ERROR, content=f"Tracker error: {e}"),
            )

    async def _save_step(self, log_id: UUID, seq: int, msg: Message) -> None:
        """Persist a single message as an execution step."""
        tool_name = None
        tool_input = None
        tool_output = None
        tool_call_id = None

        if msg.type == MessageType.TOOL_USE:
            tool_name = msg.metadata.get("tool_name") if msg.metadata else None
            tool_input = msg.metadata.get("input") if msg.metadata else None
            tool_call_id = msg.metadata.get("tool_call_id") if msg.metadata else None
        elif msg.type == MessageType.TOOL_RESULT:
            tool_name = msg.metadata.get("tool_name") if msg.metadata else None
            tool_output = msg.content
            tool_call_id = msg.metadata.get("tool_call_id") if msg.metadata else None

        try:
            self._repo.create_step(
                execution_log_id=log_id,
                seq=seq,
                step_type=msg.type.value,
                content=msg.content if msg.type != MessageType.TOOL_RESULT else None,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                tool_call_id=tool_call_id,
            )
            logger.debug(f"Step saved: log={log_id}, seq={seq}, type={msg.type.value}")
        except Exception as e:
            logger.error(f"Failed to save step {seq} for log {log_id}: {e}")

    def finalize(self, log_id: UUID, result: Result) -> bool:
        """Finalize the execution log with the result.

        Args:
            log_id: UUID of the execution_logs row.
            result: The final Result from the agent.

        Returns:
            True if successfully updated.
        """
        status = "completed" if result.error_message == "" else "failed"
        if result.error_message and "timeout" in result.error_message.lower():
            failure_reason = "timeout"
        elif result.error_message:
            failure_reason = "agent_error"
        else:
            failure_reason = None

        success = self._repo.update_log_result(
            log_id=log_id,
            status=status,
            probability=result.probability,
            confidence=result.confidence,
            reasoning=result.reasoning,
            sources=result.sources if result.sources else None,
            raw_output=result.raw_output,
            error_message=result.error_message or None,
            failure_reason=failure_reason,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            agent_name=result.agent_name or None,
            prompt_used=result.prompt_used or None,
        )
        if success:
            logger.info(f"Execution log finalized: id={log_id}, status={status}")
        return success
