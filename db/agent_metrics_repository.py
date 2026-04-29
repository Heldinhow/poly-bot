import logging
from typing import Optional

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class AgentMetricsRepository:
    """Repository for per-agent winrate and bet tracking."""

    def get_all(self):
        """Return all agent metric rows."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM agent_metrics ORDER BY agent_name")
            return cursor.fetchall()

    def get_by_name(self, agent_name: str):
        """Return a single agent's metrics."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM agent_metrics WHERE agent_name = %s",
                (agent_name,)
            )
            return cursor.fetchone()

    def get_or_create(self, agent_name: str) -> str:
        """Get existing metrics row or create new one. Returns the id."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_metrics (agent_name)
                VALUES (%s)
                ON CONFLICT (agent_name) DO UPDATE SET id = agent_metrics.id
                RETURNING id
                """,
                (agent_name,)
            )
            return cursor.fetchone()["id"]

    def record_bet(self, agent_name: str, bet_id: int) -> None:
        """Increment pending count for an agent when a bet is placed."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_metrics (agent_name, pending)
                VALUES (%s, 1)
                ON CONFLICT (agent_name) DO UPDATE SET
                    pending = agent_metrics.pending + 1,
                    updated_at = NOW()
                """,
                (agent_name,)
            )
        logger.debug(f"AgentMetrics: {agent_name} pending++ (bet_id={bet_id})")

    def record_win(self, agent_name: str, pnl: float) -> None:
        """Move a pending bet to a win: pending--, wins++, total_pnl += pnl."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_metrics SET
                    pending = GREATEST(pending - 1, 0),
                    wins = wins + 1,
                    total_pnl = total_pnl + %s,
                    updated_at = NOW()
                WHERE agent_name = %s
                """,
                (pnl, agent_name)
            )
        logger.debug(f"AgentMetrics: {agent_name} win, pnl={pnl:.2f}")

    def record_loss(self, agent_name: str, pnl: float) -> None:
        """Move a pending bet to a loss: pending--, losses++, total_pnl += pnl (pnl is negative)."""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_metrics SET
                    pending = GREATEST(pending - 1, 0),
                    losses = losses + 1,
                    total_pnl = total_pnl + %s,
                    updated_at = NOW()
                WHERE agent_name = %s
                """,
                (pnl, agent_name)
            )
        logger.debug(f"AgentMetrics: {agent_name} loss, pnl={pnl:.2f}")

    def record_skip(self, agent_name: str) -> None:
        """A bet was skipped (decision=SKIP or REJECT). Count as no bet — no pending change."""
        pass
