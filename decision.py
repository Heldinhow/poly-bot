import logging
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)


class DecisionGate:
    """Decision gate that evaluates underdog bets based on edge vs market price."""

    def __init__(
        self,
        high_threshold: Optional[float] = None,
        low_threshold: Optional[float] = None,
    ):
        settings = get_settings()
        self.high_threshold = high_threshold or settings.high_confidence_threshold
        self.low_threshold = low_threshold or settings.low_confidence_threshold

    def evaluate(self, probability: float) -> str:
        """
        Legacy: evaluate raw probability.
        
        Returns:
            "HIGH" if probability >= high_threshold
            "MEDIUM" if low_threshold <= probability < high_threshold
            "LOW" if probability < low_threshold
        """
        if probability >= self.high_threshold:
            return "HIGH"
        elif probability >= self.low_threshold:
            return "MEDIUM"
        else:
            return "LOW"

    def evaluate_edge(
        self,
        edge: float,
        ai_probability: float,
        implied_probability: float,
    ) -> str:
        """
        Evaluate bet based on edge over market-implied probability.
        
        Args:
            edge: (ai_prob * odds) - 1.0 — expected return above fair value
            ai_probability: estimated true probability from AI agents
            implied_probability: market-implied probability (underdog price)
            
        Returns:
            "HIGH" — strong value edge, recommended bet
            "MEDIUM" — modest edge, borderline
            "LOW" — weak edge, skip unless aggressive
            "REJECT" — no edge or negative edge, skip
        """
        settings = get_settings()
        min_edge = settings.min_edge
        
        # No edge or negative edge → reject
        if edge < min_edge:
            logger.debug(f"REJECT: edge {edge:.1%} < min_edge {min_edge:.1%}")
            return "REJECT"
        
        # AI thinks underdog is LESS likely than market → reject (market may know something)
        if ai_probability < implied_probability * 0.85:
            logger.debug(
                f"REJECT: ai_prob {ai_probability:.1%} < implied {implied_probability:.1%} * 0.85"
            )
            return "REJECT"
        
        # Moderate edge (5-15%) → ACCEPT
        if edge >= 0.05:
            return "ACCEPT"

        # Weak edge (<5% but >min_edge) → REJECT
        return "REJECT"

    def should_bet(self, probability: float) -> bool:
        """Return True if probability is HIGH conviction."""
        return self.evaluate(probability) == "HIGH"
