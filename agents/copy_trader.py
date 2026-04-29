"""
CopyTraderAgent — mirrors trades from watched Polymarket wallets.

This runs as a parallel flow to the main scanner. Positions from watched
wallets are first analyzed by the crypto agent to determine AI probability,
then stored as pending if edge is positive.

Supports both open positions (live) and closed positions (historical mirror).
"""
import asyncio
import logging
from typing import Optional

from data_client import PolymarketDataClient
from db.wallet_watch_list_repository import WalletWatchListRepository
from db.pending_copy_trades_repository import PendingCopyTradesRepository
from portfolio import PaperPortfolio

logger = logging.getLogger(__name__)


class CopyTraderAgent:
    """Agent that copies trades from a watched wallet list.

    Positions are analyzed by the agent runtime to determine AI probability,
    then stored as PENDING for review before confirmation.
    """

    def __init__(
        self,
        wallet_repo: WalletWatchListRepository,
        data_client: PolymarketDataClient,
        portfolio: PaperPortfolio,
        agent_runner,  # AgentRunner instance
        min_position_size: float = 10.0,
        min_odds: float = 2.0,
        max_odds: float = 10.0,
        max_price: float = 0.40,
        min_edge: float = 0.05,
    ):
        self._wallet_repo = wallet_repo
        self._data_client = data_client
        self._portfolio = portfolio
        self._pending_repo = PendingCopyTradesRepository()
        self._agent_runner = agent_runner
        self._min_size = min_position_size
        self._min_odds = min_odds
        self._max_odds = max_odds
        self._max_price = max_price
        self._min_edge = min_edge

    async def scan_wallets(self) -> int:
        """Scan all active wallets and analyze + store opportunities as PENDING."""
        stored = 0
        wallets = self._wallet_repo.get_active()
        logger.info(f"CopyTrader: scanning {len(wallets)} wallets")

        tasks = []
        for wallet in wallets:
            address = wallet["wallet_address"]
            # 1. Open positions
            positions = self._data_client.get_positions(address)
            for pos in positions:
                if self._passes_static_filters(wallet, pos):
                    tasks.append(self._analyze_and_store(wallet, pos, is_open=True))

            # 2. Closed positions
            closed = self._data_client.get_closed_positions(address)
            for pos in closed:
                pnl = float(pos.get("realizedPnl", 0) or 0)
                if pnl <= 0:
                    continue
                if self._passes_static_filters(wallet, pos):
                    tasks.append(self._analyze_and_store(wallet, pos, is_open=False))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                stored += 1
            elif isinstance(r, Exception):
                logger.warning(f"CopyTrader: analysis error: {r}")

        logger.info(f"CopyTrader: stored {stored} pending copy trades")
        return stored

    def _passes_static_filters(self, wallet: dict, position: dict) -> bool:
        """Return True if position passes basic filters (no AI call needed)."""
        import time
        market_id = position.get("conditionId") or position.get("condition_id")
        if not market_id:
            return False

        # Skip if we already have an open bet
        if self._portfolio.repository.has_open_bet_for_market(market_id):
            return False

        # Filter by age — only copy positions from last 24h
        created_ts = position.get("createdAt", 0)
        if created_ts > 0:
            age_hours = (time.time() - created_ts) / 3600
            if age_hours > 24:
                return False

        price = float(position.get("avgPrice") or position.get("curPrice") or 0)
        if price <= 0 or price > self._max_price:
            return False

        odds = 1.0 / price
        if odds < self._min_odds or odds > self._max_odds:
            return False

        size = float(position.get("size", 0) or 0)
        initial = float(position.get("initialValue", 0) or 0)
        if initial < self._min_size and size < self._min_size:
            return False

        return True

    async def _analyze_and_store(
        self, wallet: dict, position: dict, is_open: bool
    ) -> bool:
        """Analyze position with AI agent, compute edge, store as pending if positive."""
        market_id = position.get("conditionId") or position.get("condition_id")
        question = position.get("title", "Unknown")
        price = float(position.get("avgPrice") or position.get("curPrice") or 0)
        odds = 1.0 / price if price > 0 else 0

        # Call agent runtime for AI probability
        ai_prob: float | None = None
        ai_confidence: float | None = None
        ai_reasoning: str = ""
        agent_name: str | None = None

        if self._agent_runner:
            try:
                result = await self._agent_runner.analyze_market(
                    market_id=market_id,
                    question=question,
                    yes_price=price,
                    no_price=1.0 - price,
                    volume_24h=0,
                    resolution_date=None,
                )
                if result:
                    ai_prob = result.probability
                    ai_confidence = result.confidence
                    ai_reasoning = result.reasoning
                    agent_name = result.agent_name
                    logger.info(
                        f"CopyTrader: agent {agent_name} analyzed {question[:40]} "
                        f"→ AI prob={ai_prob:.2%} conf={ai_confidence or 0:.2%}"
                    )
            except Exception as e:
                logger.warning(f"CopyTrader: agent analysis failed for {market_id}: {e}")

        # Compute edge using AI probability if available, else neutral 0.5
        p = ai_prob if ai_prob is not None else 0.5
        b = odds - 1
        edge = (p * odds) - 1

        if edge <= self._min_edge:
            logger.debug(
                f"CopyTrader: insufficient edge for {question[:40]} "
                f"(edge={edge:.4f} < {self._min_edge})"
            )
            return False

        # Place bet directly — agent analysis is the confirmation
        try:
            bet = self._portfolio.record_bet(
                market_id=market_id,
                question=question,
                outcome="YES",
                price=price,
                probability_ai=ai_prob,
                analysis_summary=f"Copy trade from wallet [{wallet.get('label', wallet.get('wallet_address', '')[:10])}] | AI reasoning: {ai_reasoning[:300]}",
                agent_name=agent_name or "CopyTrader",
                source="copy",
            )
            if bet:
                logger.info(
                    f"CopyTrader: BET PLACED | {question[:50]} | "
                    f"AI={p:.0%} edge={edge:.2%} stake=${bet.stake:.2f} | "
                    f"from wallet {wallet.get('label', wallet.get('wallet_address', '')[:10])}"
                )
                return True
            else:
                logger.warning(
                    f"CopyTrader: bet rejected by portfolio (duplicate or stake=0) — {question[:40]}"
                )
                return False
        except Exception as e:
            logger.warning(f"CopyTrader: failed to place bet: {e}")
            return False

    # Sync wrapper for the API (which is not async)
    def scan_wallets_sync(self) -> int:
        """Synchronous wrapper — runs scan_wallets in an event loop."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.scan_wallets())
