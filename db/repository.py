import logging
from datetime import datetime, timezone
from typing import Optional

from db.connection import get_db_cursor
from models.bet import Bet

logger = logging.getLogger(__name__)


class BetRepository:
    """Repository for bet CRUD operations using PostgreSQL."""

    def create_bet(self, bet: Bet) -> int:
        """Insert a new bet and return its ID."""
        data = bet.to_db_dict()
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bets (
                    market_id, question, outcome, price, stake, payout,
                    kelly_frac, edge, timestamp, probability_ai, analysis_summary,
                    resolved, result, resolved_at, trading_mode
                ) VALUES (
                    %(market_id)s, %(question)s, %(outcome)s, %(price)s, %(stake)s, %(payout)s,
                    %(kelly_frac)s, %(edge)s, %(timestamp)s, %(probability_ai)s, %(analysis_summary)s,
                    %(resolved)s, %(result)s, %(resolved_at)s, %(trading_mode)s
                )
                RETURNING id
                """,
                data,
            )
            result = cursor.fetchone()
            bet_id = result["id"]
            logger.info(f"Bet created in DB: id={bet_id}, market={bet.market_id}, mode={bet.trading_mode}")
            return bet_id

    def get_open_bets(self, trading_mode: Optional[str] = None) -> list[Bet]:
        """Load unresolved bets, optionally filtered by trading_mode."""
        with get_db_cursor() as cursor:
            if trading_mode:
                cursor.execute(
                    """
                    SELECT * FROM bets
                    WHERE resolved = FALSE AND trading_mode = %s
                    ORDER BY timestamp DESC
                    """,
                    (trading_mode,),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM bets
                    WHERE resolved = FALSE
                    ORDER BY timestamp DESC
                    """
                )
            rows = cursor.fetchall()
            return [Bet.from_db_row(row) for row in rows]

    def get_bet_by_market_id(self, market_id: str, trading_mode: Optional[str] = None) -> Optional[Bet]:
        """Get a single bet by market_id."""
        with get_db_cursor() as cursor:
            if trading_mode:
                cursor.execute(
                    """
                    SELECT * FROM bets
                    WHERE market_id = %s AND trading_mode = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (market_id, trading_mode),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM bets
                    WHERE market_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (market_id,),
                )
            row = cursor.fetchone()
            return Bet.from_db_row(row) if row else None

    def has_open_bet_for_market(self, market_id: str, trading_mode: Optional[str] = None) -> bool:
        """Check if there is an unresolved bet for a given market."""
        with get_db_cursor() as cursor:
            if trading_mode:
                cursor.execute(
                    """
                    SELECT 1 FROM bets
                    WHERE market_id = %s AND resolved = FALSE AND trading_mode = %s
                    LIMIT 1
                    """,
                    (market_id, trading_mode),
                )
            else:
                cursor.execute(
                    """
                    SELECT 1 FROM bets
                    WHERE market_id = %s AND resolved = FALSE
                    LIMIT 1
                    """,
                    (market_id,),
                )
            return cursor.fetchone() is not None

    def resolve_bet(self, market_id: str, won: bool, trading_mode: Optional[str] = None) -> bool:
        """Mark a bet as resolved. Returns True if a bet was updated."""
        result_str = "win" if won else "lose"
        resolved_at = datetime.now(timezone.utc).isoformat()

        with get_db_cursor() as cursor:
            if trading_mode:
                cursor.execute(
                    """
                    UPDATE bets
                    SET resolved = TRUE, result = %s, resolved_at = %s, updated_at = NOW()
                    WHERE market_id = %s AND resolved = FALSE AND trading_mode = %s
                    RETURNING id
                    """,
                    (result_str, resolved_at, market_id, trading_mode),
                )
            else:
                cursor.execute(
                    """
                    UPDATE bets
                    SET resolved = TRUE, result = %s, resolved_at = %s, updated_at = NOW()
                    WHERE market_id = %s AND resolved = FALSE
                    RETURNING id
                    """,
                    (result_str, resolved_at, market_id),
                )
            row = cursor.fetchone()
            if row:
                logger.info(f"Bet resolved in DB: market={market_id}, result={result_str}")
                return True
            return False

    def get_bet_history(
        self,
        trading_mode: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 1000,
    ) -> list[Bet]:
        """Get bet history with optional filters."""
        conditions = []
        params = []

        if trading_mode is not None:
            conditions.append("trading_mode = %s")
            params.append(trading_mode)
        if resolved is not None:
            conditions.append("resolved = %s")
            params.append(resolved)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        with get_db_cursor() as cursor:
            cursor.execute(
                f"""
                SELECT * FROM bets
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                params + [limit],
            )
            rows = cursor.fetchall()
            return [Bet.from_db_row(row) for row in rows]

    def get_stats(self, trading_mode: Optional[str] = None) -> dict:
        """Get aggregated statistics for bets."""
        with get_db_cursor() as cursor:
            if trading_mode:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_bets,
                        COUNT(*) FILTER (WHERE resolved = FALSE) as open_bets,
                        COUNT(*) FILTER (WHERE resolved = TRUE AND result = 'win') as wins,
                        COUNT(*) FILTER (WHERE resolved = TRUE AND result = 'lose') as losses,
                        SUM(stake) as total_staked,
                        SUM(payout) FILTER (WHERE resolved = TRUE AND result = 'win') as total_won
                    FROM bets
                    WHERE trading_mode = %s
                    """,
                    (trading_mode,),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_bets,
                        COUNT(*) FILTER (WHERE resolved = FALSE) as open_bets,
                        COUNT(*) FILTER (WHERE resolved = TRUE AND result = 'win') as wins,
                        COUNT(*) FILTER (WHERE resolved = TRUE AND result = 'lose') as losses,
                        SUM(stake) as total_staked,
                        SUM(payout) FILTER (WHERE resolved = TRUE AND result = 'win') as total_won
                    FROM bets
                    """
                )
            row = cursor.fetchone()
            return {
                "total_bets": row["total_bets"] or 0,
                "open_bets": row["open_bets"] or 0,
                "wins": row["wins"] or 0,
                "losses": row["losses"] or 0,
                "total_staked": float(row["total_staked"] or 0),
                "total_won": float(row["total_won"] or 0),
            }
