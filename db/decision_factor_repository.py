"""Repository for decision_factors — decision context per market analysis."""
import logging
from uuid import UUID
from decimal import Decimal

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class DecisionFactorRepository:
    def create(self, execution_log_id: UUID, market_id: str, implied_prob: float,
               ai_prob: float, odds: float, edge: float, decision: str,
               reject_reason: str = None, bet_id: UUID = None,
               stake: float = None, kelly_frac: float = None) -> UUID:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO decision_factors
                    (execution_log_id, market_id, implied_probability, ai_probability,
                     odds, edge, decision, reject_reason, bet_id, stake, kelly_fraction)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    str(execution_log_id), market_id,
                    Decimal(str(implied_prob)), Decimal(str(ai_prob)),
                    Decimal(str(odds)), Decimal(str(edge)),
                    decision, reject_reason,
                    str(bet_id) if bet_id else None,
                    Decimal(str(stake)) if stake else None,
                    Decimal(str(kelly_frac)) if kelly_frac else None,
                ),
            )
            return cursor.fetchone()["id"]

    def update_bet_link(self, factor_id: UUID, bet_id: UUID, stake: float,
                        kelly_frac: float = None) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE decision_factors
                SET bet_id = %s, stake = %s, kelly_fraction = %s
                WHERE id = %s
                RETURNING id
                """,
                (str(bet_id), Decimal(str(stake)),
                 Decimal(str(kelly_frac)) if kelly_frac else None,
                 str(factor_id)),
            )
            return cursor.fetchone() is not None

    def list_by_market(self, market_id: str) -> list[dict]:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM decision_factors
                WHERE market_id = %s
                ORDER BY created_at ASC
                """,
                (market_id,),
            )
            return cursor.fetchall()

    def list_by_decision(self, decision: str, since=None, limit: int = 100,
                          offset: int = 0) -> list[dict]:
        with get_db_cursor() as cursor:
            if since:
                cursor.execute(
                    """
                    SELECT * FROM decision_factors
                    WHERE decision = %s AND created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (decision, since, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM decision_factors
                    WHERE decision = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (decision, limit, offset),
                )
            return cursor.fetchall()