"""Esports Analyst agent for esports underdogs."""
from typing import Any

from agents.base import BaseAgent


class EsportsAnalyst(BaseAgent):
    """Analyst specialized in esports (LoL, CS2, Valorant, Dota 2, etc.)."""

    def __init__(self):
        super().__init__(
            name="EsportsAnalyst",
            role="An expert esports analyst with deep knowledge of competitive gaming. You track team compositions, player form, patch metas, tournament formats, and map-specific performance for games like League of Legends, Counter-Strike 2, Valorant, and Dota 2.",
            temperature=0.5,
            max_tokens=1024,
        )

    @property
    def prompt(self) -> str:
        return (
            f"You are {self.name}, {self.role}\n\n"
            "Your task is to analyze an esports betting market and estimate the TRUE probability of the underdog winning.\n\n"
            "Consider:\n"
            "- Current patch meta and champion/agent pool strengths\n"
            "- Team roster stability and recent substitutions\n"
            "- Map/region specific performance\n"
            "- Tournament format (BO1 vs BO3 vs BO5)\n"
            "- Recent match history and momentum\n"
            "- Player individual skill and form\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"probability": 0.XX, "confidence": 0.XX, "reasoning": "Brief explanation"}\n'
            "probability: your estimated true probability (0.0 to 1.0)\n"
            "confidence: how confident you are in this estimate (0.0 to 1.0)\n"
            "reasoning: one sentence explaining your key insight"
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze an esports market and return probability estimate."""
        from client import Market
        
        market = context if isinstance(context, Market) else None
        if not market:
            return {"probability": 0.5, "confidence": 0.0, "reasoning": "Invalid market data"}

        underdog_price = min(market.yes_price, market.no_price)
        favorite_price = max(market.yes_price, market.no_price)
        underdog_outcome = market.outcomes[0].outcome if market.yes_price < market.no_price else market.outcomes[1].outcome

        prompt = (
            f"Market: {market.question}\n"
            f"Underdog: {underdog_outcome} @ {underdog_price:.2%}\n"
            f"Favorite: @ {favorite_price:.2%}\n"
            f"Volume 24h: ${market.volume_24h:,.0f}\n"
            f"Resolution: {market.resolution_date}\n\n"
            "Estimate the TRUE probability of the underdog winning."
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
