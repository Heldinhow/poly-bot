import json
import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class MarketOutcome:
    outcome: str
    price: float


@dataclass
class Market:
    id: str
    condition_id: str
    question: str
    outcomes: List[MarketOutcome]
    yes_price: float
    no_price: float
    volume_24h: float
    volume: float
    liquidity: float
    slug: str
    url: str
    resolution_date: Optional[str]

    @staticmethod
    def from_api(data: dict) -> "Market":
        raw_prices = data.get("outcomePrices") or "[]"
        if isinstance(raw_prices, str):
            raw_prices = json.loads(raw_prices)
        outcome_prices: List[float] = [float(p) for p in raw_prices]

        raw_outcomes = data.get("outcomes") or []
        if isinstance(raw_outcomes, str):
            raw_outcomes = json.loads(raw_outcomes)
        outcomes_raw: List[str] = list(raw_outcomes)

        if len(outcome_prices) >= 2:
            p0, p1 = outcome_prices[0], outcome_prices[1]
            if p0 <= p1:
                yes_price, no_price = p0, p1
            else:
                yes_price, no_price = p1, p0
        else:
            yes_price, no_price = 0.0, 0.0

        outcomes = [
            MarketOutcome(
                outcome=str(outcomes_raw[i]) if i < len(outcomes_raw) else "",
                price=outcome_prices[i] if i < len(outcome_prices) else 0.0,
            )
            for i in range(len(outcomes_raw))
        ]

        res_date = data.get("endDate") or data.get("endDateIso") or None
        slug = data.get("slug", "") or ""
        url = f"https://polymarket.com/market/{slug}" if slug else "https://polymarket.com"

        return Market(
            id=str(data.get("id", "")),
            condition_id=str(data.get("conditionId", "")),
            question=str(data.get("question", "")),
            outcomes=outcomes,
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=float(data.get("volume24hr") or 0),
            volume=float(data.get("volume") or 0),
            liquidity=float(data.get("liquidity") or 0),
            slug=slug,
            url=url,
            resolution_date=res_date,
        )


class PolymarketClient:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self) -> None:
        self._http = httpx.Client(timeout=30.0)
        settings = get_settings()
        self.base_url = settings.polymarket_api_url or self.BASE_URL
        logger.info("PolymarketClient initialized")

    def close(self) -> None:
        self._http.close()

    def fetch_active_markets(self, limit: int = 200) -> List[Market]:
        try:
            params = {
                "closed": "false",
                "limit": limit,
                "order": "volume24hr",
                "ascending": "false",
            }
            resp = self._http.get(f"{self.base_url}/markets", params=params)
            resp.raise_for_status()
            raw = resp.json()
            markets = [Market.from_api(m) for m in raw]
            logger.debug(f"Fetched {len(markets)} markets")
            return markets
        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def filter_markets(
        self, markets: List[Market], predicate: Callable[[Market], bool]
    ) -> List[Market]:
        return [m for m in markets if predicate(m)]
