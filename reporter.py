import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class MarketResolver:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self, http_client: httpx.Client):
        self._http = http_client

    def check_resolved(self, market_id: str) -> Optional[bool]:
        """Returns True if underdog won, False if lost, None if not resolved yet."""
        try:
            resp = self._http.get(f"{self.BASE_URL}/markets/{market_id}", timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data.get("closed", False):
                return None

            raw_prices = data.get("outcomePrices") or "[]"
            if isinstance(raw_prices, str):
                raw_prices = json.loads(raw_prices)
            prices = [float(p) for p in raw_prices]

            raw_outcomes = data.get("outcomes") or []
            if isinstance(raw_outcomes, str):
                raw_outcomes = json.loads(raw_outcomes)

            if len(prices) < 2 or len(raw_outcomes) < 2:
                return None

            # Winner: outcome with price closest to 1.0
            winner_idx = 0 if abs(prices[0] - 1.0) < abs(prices[1] - 1.0) else 1
            return raw_outcomes[winner_idx]

        except Exception as e:
            logger.warning(f"Resolution check failed for {market_id}: {e}")
            return None

    def resolve_portfolio(self, portfolio) -> int:
        open_bets = portfolio.get_open_bets()
        if not open_bets:
            return 0

        resolved = 0
        for bet in open_bets:
            winner = self.check_resolved(bet.market_id)
            if winner is None:
                continue
            won = winner == bet.outcome
            portfolio.resolve_bet(bet.market_id, won)
            resolved += 1

        if resolved:
            logger.info(f"Resolved {resolved}/{len(open_bets)} open bets")
        return resolved
