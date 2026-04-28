"""Sports Analyst agent for traditional sports underdogs."""
from typing import Any

from agents.base import BaseAgent


class SportsAnalyst(BaseAgent):
    """Analyst specialized in traditional sports (NBA, tennis, MLB, etc.)."""

    def __init__(self):
        super().__init__(
            name="SportsAnalyst",
            role="A seasoned sports analyst with deep expertise in traditional sports statistics, player form, team dynamics, and historical performance. You analyze NBA, tennis, MLB, and other traditional sports markets.",
            temperature=0.5,
            max_tokens=1024,
        )

    @property
    def prompt(self) -> str:
        return (
            f"You are {self.name}, {self.role}\n\n"
            "Your task is to analyze a sports betting market and estimate the TRUE probability of the underdog winning.\n\n"
            "Consider:\n"
            "- Recent team/player form (last 5-10 games)\n"
            "- Head-to-head history\n"
            "- Home/away advantage\n"
            "- Injuries or lineup changes\n"
            "- Tournament/match importance\n"
            "- Weather conditions (for outdoor sports)\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            '{"probability": 0.XX, "confidence": 0.XX, "reasoning": "Brief explanation"}\n'
            "probability: your estimated true probability (0.0 to 1.0)\n"
            "confidence: how confident you are in this estimate (0.0 to 1.0)\n"
            "reasoning: one sentence explaining your key insight"
        )

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze a sports market and return probability estimate."""
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
        
        # Parse JSON response
        try:
            import json
            import re
            # Extract JSON from response
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

        # Fallback: return 50% if parsing fails
        return {"probability": 0.5, "confidence": 0.0, "reasoning": "Failed to parse AI response"}
