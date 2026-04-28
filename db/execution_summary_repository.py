"""Repository for execution_summary — denormalized audit trail per market."""
import logging
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class ExecutionSummaryRepository:
    def upsert_from_market(
        self,
        market_id: str,
        question: str,
        yes_price: float,
        no_price: float,
        volume_24h: float,
        resolution_date: str,
        agent_names: list[str],
        probabilities: list[float],
        confidences: list[float],
        reasoning_summary: str,
        decision: str,
        reject_reason: str,
        edge: float,
        first_execution_id: UUID,
        last_execution_id: UUID,
        execution_count: int,
    ) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO execution_summary
                    (market_id, question, yes_price_at_analysis, no_price_at_analysis,
                     volume_24h, resolution_date, agent_names, probabilities, confidences,
                     reasoning_summary, decision, reject_reason, edge,
                     first_execution_id, last_execution_id, execution_count, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (market_id) DO UPDATE SET
                    question = EXCLUDED.question,
                    yes_price_at_analysis = EXCLUDED.yes_price_at_analysis,
                    no_price_at_analysis = EXCLUDED.no_price_at_analysis,
                    volume_24h = EXCLUDED.volume_24h,
                    resolution_date = EXCLUDED.resolution_date,
                    agent_names = EXCLUDED.agent_names,
                    probabilities = EXCLUDED.probabilities,
                    confidences = EXCLUDED.confidences,
                    reasoning_summary = EXCLUDED.reasoning_summary,
                    decision = EXCLUDED.decision,
                    reject_reason = EXCLUDED.reject_reason,
                    edge = EXCLUDED.edge,
                    last_execution_id = EXCLUDED.last_execution_id,
                    execution_count = EXCLUDED.execution_count + 1,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    market_id, question,
                    Decimal(str(yes_price)), Decimal(str(no_price)),
                    Decimal(str(volume_24h)), resolution_date,
                    agent_names,
                    [Decimal(str(p)) for p in probabilities],
                    [Decimal(str(c)) for c in confidences],
                    reasoning_summary, decision, reject_reason,
                    Decimal(str(edge)),
                    str(first_execution_id), str(last_execution_id),
                    execution_count,
                ),
            )
            return cursor.fetchone()["id"]

    def update_bet_link(self, market_id: str, bet_id: UUID, stake: float,
                         outcome: str) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE execution_summary
                SET bet_id = %s, stake = %s, outcome = %s, updated_at = NOW()
                WHERE market_id = %s
                RETURNING id
                """,
                (str(bet_id), Decimal(str(stake)), outcome, market_id),
            )
            return cursor.fetchone() is not None

    def update_bet_result(self, bet_id: UUID, result: str) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE execution_summary
                SET bet_result = %s, updated_at = NOW()
                WHERE bet_id = %s
                RETURNING id
                """,
                (result, str(bet_id)),
            )
            return cursor.fetchone() is not None

    def get_market_summary(self, market_id: str) -> dict | None:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM execution_summary WHERE market_id = %s",
                (market_id,),
            )
            return cursor.fetchone()

    def list_summaries(self, decision: str = None, since: datetime = None,
                       bet_result: str = None, limit: int = 100,
                       offset: int = 0) -> list[dict]:
        conditions = []
        params = []
        if decision:
            conditions.append("decision = %s")
            params.append(decision)
        if since:
            conditions.append("created_at >= %s")
            params.append(since)
        if bet_result:
            conditions.append("bet_result = %s")
            params.append(bet_result)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with get_db_cursor() as cursor:
            cursor.execute(
                f"""
                SELECT * FROM execution_summary
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            return cursor.fetchall()