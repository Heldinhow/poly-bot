"""Repository for market_analysis_cache — avoid re-analyzing same markets."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from decimal import Decimal

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)

# Price change threshold to trigger re-analysis
PRICE_CHANGE_THRESHOLD = 0.05  # 5%
# Minimum time between re-analyses (even if price changed)
MIN_REANALYSIS_INTERVAL = timedelta(minutes=10)


class CacheRepository:
    """Cache for market analysis results to avoid redundant AI calls."""

    def get_cache(self, market_id: str) -> Optional[dict]:
        """Get cached analysis for a market."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM market_analysis_cache WHERE market_id = %s",
                (market_id,),
            )
            return cursor.fetchone()

    def set_cache(
        self,
        market_id: str,
        question: str,
        yes_price: float,
        no_price: float,
        probability: Optional[float] = None,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
        agent_name: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> bool:
        """Cache analysis result for a market."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO market_analysis_cache
                        (market_id, question, yes_price_at_analysis, no_price_at_analysis,
                         probability, confidence, reasoning, agent_name, decision, analyzed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (market_id) DO UPDATE SET
                        question = EXCLUDED.question,
                        yes_price_at_analysis = EXCLUDED.yes_price_at_analysis,
                        no_price_at_analysis = EXCLUDED.no_price_at_analysis,
                        probability = EXCLUDED.probability,
                        confidence = EXCLUDED.confidence,
                        reasoning = EXCLUDED.reasoning,
                        agent_name = EXCLUDED.agent_name,
                        decision = EXCLUDED.decision,
                        analyzed_at = NOW()
                    """,
                    (
                        market_id, question,
                        Decimal(str(yes_price)), Decimal(str(no_price)),
                        Decimal(str(probability)) if probability is not None else None,
                        Decimal(str(confidence)) if confidence is not None else None,
                        reasoning, agent_name, decision,
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"Error caching analysis for {market_id}: {e} — {type(e).__name__}")
            # Write fallback to execution_logs so next scan still skips this market
            self._write_fallback_to_execution_logs(market_id, question, probability)
            raise  # Re-raise so caller knows something is wrong

    def should_analyze(
        self,
        market_id: str,
        current_yes_price: float,
        current_no_price: float,
    ) -> bool:
        """Check if a market should be analyzed based on cache.

        Returns True if:
        - Never analyzed before (and no recent executions)
        - Was REJECTED and price changed more than threshold
        - Last analysis was more than MIN_REANALYSIS_INTERVAL ago and price moved

        Returns False if:
        - Was ACCEPTED (already bet on it)
        - Recently executed (even if cache write failed)
        - Was REJECTED and price is stable (< threshold change)
        - Analyzed too recently (within MIN_REANALYSIS_INTERVAL)
        """
        cache = self.get_cache(market_id)

        # Never analyzed — check execution_logs as fallback
        if not cache:
            if self._was_recently_executed(market_id):
                logger.info(f"Skipping {market_id}: recently executed (cache miss, log hit)")
                return False
            return True

        # Already bet on this market — don't re-analyze
        if cache.get("decision") == "ACCEPT":
            return False

        # Another scan is currently analyzing this market — skip
        if cache.get("decision") == "IN_PROGRESS":
            logger.info(f"Skipping {market_id}: claim in progress by another scan")
            return False

        # Check time since last analysis
        analyzed_at = cache.get("analyzed_at")
        if analyzed_at:
            if analyzed_at.tzinfo is None:
                analyzed_at = analyzed_at.replace(tzinfo=timezone.utc)
            time_since = datetime.now(timezone.utc) - analyzed_at

            # Too soon to re-analyze (even if price moved)
            if time_since < MIN_REANALYSIS_INTERVAL:
                return False

        # Check if price changed significantly
        cached_yes = float(cache.get("yes_price_at_analysis", 0))
        cached_no = float(cache.get("no_price_at_analysis", 0))

        yes_change = abs(current_yes_price - cached_yes)
        no_change = abs(current_no_price - cached_no)

        # Price changed significantly — should re-analyze
        if yes_change >= PRICE_CHANGE_THRESHOLD or no_change >= PRICE_CHANGE_THRESHOLD:
            return True

        # Price is stable — skip
        logger.debug(
            f"Cache hit for {market_id}: price stable "
            f"(yes: {cached_yes:.2%} → {current_yes_price:.2%}, "
            f"no: {cached_no:.2%} → {current_no_price:.2%})"
        )
        return False

    def _write_fallback_to_execution_logs(
        self,
        market_id: str,
        question: str,
        probability: Optional[float] = None,
    ) -> None:
        """Write a fallback marker to execution_logs when cache write fails.

        This ensures the market is still marked as recently analyzed
        so _was_recently_executed() returns True on the next scan.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_logs
                        (task_id, market_id, agent_name, runtime, status, reasoning, probability)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        f"cache-fallback-{market_id}",
                        market_id,
                        "cache-fallback",
                        "fallback",
                        "completed",
                        f"Cache write failed for market {market_id}",
                        Decimal(str(probability)) if probability is not None else None,
                    ),
                )
                logger.info(f"[FALLBACK] Wrote execution_logs marker for {market_id} after cache failure")
        except Exception as e:
            logger.warning(f"[FALLBACK] Failed to write execution_logs marker for {market_id}: {e}")

    def _was_recently_executed(self, market_id: str) -> bool:
        """Check if there's a recent execution for this market (fallback for cache misses).

        Also serves as fallback path when market_analysis_cache write fails —
        after a failed cache write, _write_fallback_to_execution_logs creates an
        execution_logs entry so this method returns True and prevents re-analysis.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """SELECT 1 FROM execution_logs
                       WHERE market_id = %s
                       AND created_at > NOW() - INTERVAL '10 minutes'
                       LIMIT 1""",
                    (market_id,),
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    def claim_market(self, market_id: str) -> bool:
        """Atomically claim a market for analysis. Returns True if claimed, False if already claimed by another scan.

        Uses ON CONFLICT DO UPDATE to atomically set decision='IN_PROGRESS'.
        Only succeeds if no existing decision or previous claim expired.
        """
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO market_analysis_cache (market_id, question, yes_price_at_analysis, no_price_at_analysis, decision, analyzed_at)
                    VALUES (%s, '', 0, 0, 'IN_PROGRESS', NOW())
                    ON CONFLICT (market_id) DO UPDATE
                        SET decision = 'IN_PROGRESS', analyzed_at = NOW()
                        WHERE market_analysis_cache.decision IS NULL
                           OR market_analysis_cache.decision NOT IN ('IN_PROGRESS', 'ACCEPT')
                    """,
                    (market_id,),
                )
                # Check if we actually claimed it (row was inserted or updated)
                cursor.execute(
                    "SELECT 1 FROM market_analysis_cache WHERE market_id = %s AND decision = 'IN_PROGRESS'",
                    (market_id,),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"[CLAIM] Failed to claim market {market_id}: {e}")
            return False

    def release_claim(self, market_id: str, decision: str) -> bool:
        """Release a market claim and set final decision (ACCEPT or REJECT)."""
        if decision not in ('ACCEPT', 'REJECT'):
            logger.warning(f"[RELEASE] Invalid decision '{decision}' for market {market_id}")
            return False
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE market_analysis_cache
                    SET decision = %s, analyzed_at = NOW()
                    WHERE market_id = %s AND decision = 'IN_PROGRESS'
                    """,
                    (decision, market_id),
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"[RELEASE] Failed to release claim for market {market_id}: {e}")
            return False

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE decision = 'ACCEPT') as accepted,
                    COUNT(*) FILTER (WHERE decision = 'REJECT') as rejected,
                    COUNT(*) FILTER (WHERE decision = 'SKIP') as skipped,
                    COUNT(*) FILTER (WHERE analyzed_at > NOW() - INTERVAL '1 hour') as last_hour
                FROM market_analysis_cache
            """)
            return cursor.fetchone()
