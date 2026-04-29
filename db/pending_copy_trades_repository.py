import logging
from dataclasses import dataclass
from typing import Optional

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class PendingCopyTradesRepository:
    """Repository for pending copy trades awaiting review before confirmation."""

    def create(
        self,
        wallet_id: str,
        wallet_address: str,
        position: dict,
        is_open: bool,
        ai_probability: float | None = None,
        ai_confidence: float | None = None,
        ai_reasoning: str | None = None,
        edge: float = 0,
        agent_name: str | None = None,
    ) -> str:
        price = float(position.get("avgPrice") or position.get("curPrice") or 0)
        odds = 1.0 / price if price > 0 else 0
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pending_copy_trades
                (wallet_id, wallet_address, condition_id, title, outcome, avg_price, odds, initial_value, realized_pnl, is_open, ai_probability, ai_confidence, ai_reasoning, edge, agent_name, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (
                    wallet_id,
                    wallet_address,
                    position.get("conditionId"),
                    position.get("title", "Unknown")[:500],
                    position.get("outcome", "YES"),
                    price,
                    odds,
                    float(position.get("initialValue", 0) or 0),
                    float(position.get("realizedPnl", 0) or 0),
                    is_open,
                    ai_probability,
                    ai_confidence,
                    ai_reasoning,
                    edge,
                    agent_name,
                ),
            )
            return cursor.fetchone()["id"]

    def get_pending(self):
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM pending_copy_trades WHERE status = 'pending' ORDER BY created_at DESC"
            )
            return cursor.fetchall()

    def confirm(self, pending_id: str) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE pending_copy_trades SET status = 'confirmed' WHERE id = %s",
                (pending_id,)
            )
            return cursor.rowcount > 0

    def reject(self, pending_id: str) -> bool:
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE pending_copy_trades SET status = 'rejected' WHERE id = %s",
                (pending_id,)
            )
            return cursor.rowcount > 0

    def delete_pending_for_wallet(self, wallet_id: str) -> int:
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM pending_copy_trades WHERE wallet_id = %s AND status = 'pending'",
                (wallet_id,)
            )
            return cursor.rowcount
