import logging
from typing import Optional
from uuid import UUID

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class ExecutionRepository:
    """Repository for execution_logs and execution_steps CRUD."""

    # ------------------------------------------------------------------
    # execution_logs
    # ------------------------------------------------------------------

    def create_log(
        self,
        task_id: str,
        market_id: str,
        agent_id: UUID,
        runtime: str,
        model: Optional[str] = None,
    ) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO execution_logs (task_id, market_id, agent_id, runtime, model)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (task_id, market_id, str(agent_id), runtime, model),
            )
            result = cursor.fetchone()
            log_id = result["id"]
            logger.info(f"Execution log created: id={log_id}, task={task_id}")
            return log_id

    def claim_log(self, log_id: UUID, runtime: str) -> bool:
        """Mark a log as claimed by a specific runtime. Returns True if successful."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE execution_logs
                SET status = 'claimed', runtime = %s
                WHERE id = %s AND status = 'queued'
                RETURNING id
                """,
                (runtime, str(log_id)),
            )
            result = cursor.fetchone()
            return result is not None

    def start_log(self, log_id: UUID) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE execution_logs
                SET status = 'running', started_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (str(log_id),),
            )
            return cursor.fetchone() is not None

    def update_log_result(
        self,
        log_id: UUID,
        status: str,
        probability: Optional[float] = None,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
        sources: Optional[list[str]] = None,
        raw_output: Optional[str] = None,
        error_message: Optional[str] = None,
        failure_reason: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE execution_logs
                SET status = %s,
                    completed_at = NOW(),
                    probability = %s,
                    confidence = %s,
                    reasoning = %s,
                    sources = %s,
                    raw_output = %s,
                    error_message = %s,
                    failure_reason = %s,
                    input_tokens = %s,
                    output_tokens = %s,
                    duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE id = %s
                RETURNING id
                """,
                (
                    status, probability, confidence, reasoning,
                    sources, raw_output, error_message, failure_reason,
                    input_tokens, output_tokens, str(log_id),
                ),
            )
            result = cursor.fetchone()
            if result:
                logger.info(f"Execution log finalized: id={log_id}, status={status}")
                return True
            return False

    def get_log(self, log_id: UUID) -> Optional[dict]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM execution_logs WHERE id = %s", (str(log_id),))
            return cursor.fetchone()

    def list_logs(
        self,
        market_id: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions = []
        params = []
        if market_id:
            conditions.append("market_id = %s")
            params.append(market_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(str(agent_id))
        if status:
            conditions.append("status = %s")
            params.append(status)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with get_db_cursor() as cursor:
            cursor.execute(
                f"""
                SELECT * FROM execution_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            return cursor.fetchall()

    # ------------------------------------------------------------------
    # execution_steps
    # ------------------------------------------------------------------

    def create_step(
        self,
        execution_log_id: UUID,
        seq: int,
        step_type: str,
        content: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[dict] = None,
        tool_output: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO execution_steps (
                    execution_log_id, seq, step_type, content,
                    tool_name, tool_input, tool_output, tool_call_id, duration_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    str(execution_log_id), seq, step_type, content,
                    tool_name, tool_input, tool_output, tool_call_id, duration_ms,
                ),
            )
            result = cursor.fetchone()
            return result["id"]

    def list_steps(self, execution_log_id: UUID) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM execution_steps
                WHERE execution_log_id = %s
                ORDER BY seq ASC
                """,
                (str(execution_log_id),),
            )
            return cursor.fetchall()
