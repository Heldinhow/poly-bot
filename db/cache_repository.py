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
        except Exception:
            logger.exception(f"Error caching analysis for {market_id}")
            return False

    def should_analyze(
        self,
        market_id: str,
        current_yes_price: float,
        current_no_price: float,
    ) -> bool:
        """Check if a market should be analyzed based on cache.

        Returns True if:
        - Never analyzed before
        - Was REJECTED and price changed more than threshold
        - Last analysis was more than MIN_REANALYSIS_INTERVAL ago and price moved

        Returns False if:
        - Was ACCEPTED (already bet on it)
        - Was REJECTED and price is stable (< threshold change)
        - Analyzed too recently (within MIN_REANALYSIS_INTERVAL)
        """
        cache = self.get_cache(market_id)

        # Never analyzed — should analyze
        if not cache:
            return True

        # Already bet on this market — don't re-analyze
        if cache.get("decision") == "ACCEPT":
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
