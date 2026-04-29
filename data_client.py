"""
Polymarket Data API client for wallet positions and trades.
https://data-api.polymarket.com
"""
import logging
import json
from typing import Optional
from urllib.request import urlopen, Request

logger = logging.getLogger(__name__)

BASE_URL = "https://data-api.polymarket.com"


class PolymarketDataClient:
    """Client for the Polymarket Data API — wallet positions, trades, activity."""

    def _request(self, url: str) -> dict | list | None:
        """Make a GET request with User-Agent header (required by Data API)."""
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.warning(f"Data API request failed: {e}")
            return None

    def get_positions(self, wallet_address: str) -> list[dict]:
        """Fetch current open positions for a wallet via /trades endpoint.

        Uses /trades?maker_address= as /positions is not functional.
        BUY trades with recent timestamps indicate open positions.
        """
        url = f"{BASE_URL}/trades?maker_address={wallet_address}&limit=100"
        data = self._request(url)
        if not isinstance(data, list):
            return []

        # Deduplicate by conditionId — BUY = open position, SELL = closing
        # Sort by timestamp descending to get most recent first
        seen = {}
        for t in data:
            cid = t.get("conditionId")
            if cid and cid not in seen and t.get("side") == "BUY":
                seen[cid] = t

        # Convert to position-like dict
        positions = []
        for cid, t in seen.items():
            price = float(t.get("price", 0))
            if price <= 0:
                continue
            positions.append({
                "conditionId": cid,
                "title": t.get("title", t.get("conditionDescription", "Unknown")),
                "avgPrice": price,
                "curPrice": price,
                "size": t.get("amount", t.get("size", 0)),
                "initialValue": t.get("value", 0),
                "createdAt": t.get("timestamp"),
            })
        return positions

    def get_closed_positions(self, wallet_address: str) -> list[dict]:
        """Fetch closed positions for a wallet via /trades (SELL = position closed)."""
        url = f"{BASE_URL}/trades?maker_address={wallet_address}&limit=100"
        data = self._request(url)
        if not isinstance(data, list):
            return []

        # SELL = closing a position; get only recent ones (last 48h)
        import time as _time
        cutoff = _time.time() - (48 * 3600)
        seen = {}
        for t in data:
            cid = t.get("conditionId")
            ts = t.get("timestamp", 0)
            if not cid or not ts:
                continue
            # Only SELL for closed positions, recent ones
            if t.get("side") == "SELL" and ts >= cutoff and cid not in seen:
                seen[cid] = t

        positions = []
        for cid, t in seen.items():
            price = float(t.get("price", 0))
            if price <= 0:
                continue
            positions.append({
                "conditionId": cid,
                "title": t.get("title", t.get("conditionDescription", "Unknown")),
                "avgPrice": price,
                "realizedPnl": t.get("realizedPnl", t.get("profit", 0)),
                "createdAt": t.get("timestamp"),
            })
        return positions

    def get_trades(self, wallet_address: str, before: Optional[int] = None) -> list[dict]:
        """Fetch trade history for a wallet."""
        url = f"{BASE_URL}/trades?maker_address={wallet_address}&limit=100"
        if before:
            url += f"&before={before}"
        data = self._request(url)
        if isinstance(data, dict):
            return data.get("data", [])
        return []

    def get_value(self, wallet_address: str) -> dict:
        """Fetch total position value for a wallet."""
        url = f"{BASE_URL}/value?user={wallet_address}"
        data = self._request(url)
        return data if isinstance(data, dict) else {}
