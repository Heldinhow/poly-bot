"""Odds Analyst agent for probability modeling."""
from typing import Any

from agents.base import BaseAgent


class OddsAnalyst(BaseAgent):
    """Analyst specialized in odds comparison and probability modeling."""

    def __init__(self):
        super().__init__(
            name="OddsAnalyst",
            role="A quantitative analyst specializing in odds modeling, market efficiency, and probability theory. You identify discrepancies between market-implied probabilities and true probabilities using statistical methods.",
            temperature=0.3,
            max_tokens=1024,
        )

    @property
    def prompt(self) -> str:
        return (
            f"You are {self.name}, {self.role}\n\n"
            "Your task is to analyze market odds and estimate the TRUE probability of the underdog winning.\n\n"
            "Consider:\n"
            "- Market-implied probability vs fair probability\n"
            "- Volume and liquidity indicators\n"
            "- Price movements (if available)\n"
            "- Market efficiency factors\n"
            "- The favorite's true strength based on odds\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"probability": 0.XX, "confidence": 0.XX, "reasoning": "Brief explanation"}\n'
            "probability: your estimated true probability (0.0 to 1.0)\n"
            "confidence: how confident you are in this estimate (0.0 to 1.0)\n"
            "reasoning: one sentence explaining your key insight"
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze market odds and return probability estimate."""
        from client import Market
        
        market = context if isinstance(context, Market) else None
        if not market:
            return {"probability": 0.5, "confidence": 0.0, "reasoning": "Invalid market data"}

        underdog_price = min(market.yes_price, market.no_price)
        favorite_price = max(market.yes_price, market.no_price)
        underdog_outcome = market.outcomes[0].outcome if market.yes_price < market.no_price else market.outcomes[1].outcome
        
        # Calculate implied probability
        implied_prob = underdog_price
        edge_vs_implied = (1.0 / underdog_price) - 1

        prompt = (
            f"Market: {market.question}\n"
            f"Underdog: {underdog_outcome}\n"
            f"Market-implied probability: {implied_prob:.2%}\n"
            f"Underdog price: {underdog_price:.4f}\n"
            f"Favorite price: {favorite_price:.4f}\n"
            f"Volume 24h: ${market.volume_24h:,.0f}\n"
            f"Liquidity: ${market.liquidity:,.0f}\n"
            f"Payout odds: {1/underdog_price:.2f}:1\n\n"
            "Estimate the TRUE probability of the underdog winning. Consider that the market-implied probability may not reflect the true odds."
        )

        response = await self.think(prompt)
        
        try:
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "probability": float(data.get("probability", 0.5)),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reasoning": str(data.get("reasoning", "No reasoning provided")),
                }
        except Exception:
            pass

        return {"probability": 0.5, "confidence": 0.0, "reasoning": "Failed to parse AI response"}
