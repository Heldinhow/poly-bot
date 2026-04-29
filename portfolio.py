import logging
import math
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from db.repository import BetRepository
from db.agent_metrics_repository import AgentMetricsRepository
from models.bet import Bet
from trading.mode_gate import TradingModeGate

logger = logging.getLogger(__name__)


class PaperPortfolio:
    """Portfolio manager using PostgreSQL for persistence.

    All bets are stored in the database. CSV is no longer used.
    """

    def __init__(
        self,
        repository: BetRepository,
        mode_gate: TradingModeGate,
        initial_bankroll: float,
        kelly_frac: float,
        min_edge: float,
    ):
        self.repository = repository
        self.mode_gate = mode_gate
        self.initial_bankroll = initial_bankroll
        self.kelly_frac = kelly_frac
        self.min_edge = min_edge
        self.bankroll = initial_bankroll
        self._agent_metrics = AgentMetricsRepository()

        # Load open bets from DB and recalculate bankroll
        self.bets: list[Bet] = self.repository.get_open_bets()
        self._recalculate_bankroll()

        logger.info(
            f"PaperPortfolio: bankroll=${self.bankroll:.2f}, "
            f"Kelly={kelly_frac:.0%}, min_edge={min_edge:.0%}, "
            f"open_bets={len(self.bets)}, mode={self.mode_gate.get_current_mode()}"
        )

    def _recalculate_bankroll(self) -> None:
        """Recalculate bankroll based on initial amount minus stakes of open bets."""
        total_staked = sum(b.stake for b in self.bets)
        self.bankroll = self.initial_bankroll - total_staked

        # Add back resolved wins
        resolved = self.repository.get_bet_history(
            trading_mode=self.mode_gate.get_current_mode(),
            resolved=True,
            limit=10000,
        )
        for bet in resolved:
            if bet.result == "win":
                self.bankroll += bet.payout

    def _kelly_stake(self, odds: float, probability_ai: Optional[float] = None) -> tuple[float, float]:
        """Kelly: stake = frac * (b*p - q) / b."""
        b = odds - 1
        if b <= 0:
            return 0.0, 0.0

        p = probability_ai if probability_ai is not None else 1.0 / odds
        q = 1.0 - p

        edge = (p * odds) - 1
        if edge <= self.min_edge:
            return 0.0, edge

        kelly_pct = self.kelly_frac * (b * p - q) / b
        stake = kelly_pct * self.bankroll
        stake = max(stake, 1.00)
        return stake, edge

    def record_bet(
        self,
        market_id: str,
        question: str,
        outcome: str,
        price: float,
        probability_ai: Optional[float] = None,
        analysis_summary: str = "",
        agent_name: Optional[str] = None,
        source: str = "scan",
    ) -> Optional[Bet]:
        """Record a new bet in the database."""
        # Check for duplicate open bet via repository
        if self.repository.has_open_bet_for_market(
            market_id, self.mode_gate.get_current_mode()
        ):
            return None

        payout_odds = 1.0 / price
        stake, edge = self._kelly_stake(payout_odds, probability_ai)
        if stake <= 0:
            return None

        stake = min(stake, self.bankroll * 0.1)
        payout = stake * payout_odds
        now = datetime.now(timezone.utc).isoformat()

        bet = Bet(
            market_id=market_id,
            question=question,
            outcome=outcome,
            price=price,
            stake=stake,
            payout=payout,
            kelly_frac=self.kelly_frac,
            edge=edge,
            timestamp=now,
            probability_ai=probability_ai,
            analysis_summary=analysis_summary,
            trading_mode=self.mode_gate.get_mode_for_bet(),
            agent_name=agent_name,
            source=source,
        )

        # Persist to database
        bet_id = self.repository.create_bet(bet)
        bet.id = bet_id
        self.bets.append(bet)
        self.bankroll -= stake

        logger.info(
            f"Bet recorded: {question[:50]} | ${stake:.2f} @ {price*100:.1f}% "
            f"| payout=${payout:.2f} | bankroll=${self.bankroll:.2f} "
            f"| mode={bet.trading_mode}"
            f"{' | AI prob=' + f'{probability_ai:.1%}' if probability_ai else ''}"
        )
        return bet

    def resolve_bet(self, market_id: str, won: bool) -> None:
        """Resolve a bet by market_id."""
        updated = self.repository.resolve_bet(
            market_id, won, self.mode_gate.get_current_mode()
        )
        if not updated:
            logger.warning(f"No open bet found to resolve for market {market_id}")
            return

        # Update local state
        for bet in self.bets:
            if bet.market_id == market_id and not bet.resolved:
                bet.resolved = True
                bet.result = "win" if won else "lose"
                bet.resolved_at = datetime.now(timezone.utc).isoformat()
                if won:
                    self.bankroll += bet.payout
                # Record against agent metrics
                if bet.agent_name:
                    pnl = bet.payout - bet.stake if won else -bet.stake
                    if won:
                        self._agent_metrics.record_win(bet.agent_name, pnl)
                    else:
                        self._agent_metrics.record_loss(bet.agent_name, pnl)
                logger.info(
                    f"Bet resolved: {bet.question[:50]} | {bet.result} "
                    f"| bankroll=${self.bankroll:.2f}"
                )
                return

    def get_open_bets(self) -> list[Bet]:
        return [b for b in self.bets if not b.resolved]

    def get_resolved_bets(self) -> list[Bet]:
        return self.repository.get_bet_history(
            trading_mode=self.mode_gate.get_current_mode(),
            resolved=True,
            limit=10000,
        )

    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio from resolved bets."""
        resolved = self.get_resolved_bets()
        if not resolved:
            return 0.0

        returns = []
        for bet in resolved:
            if bet.result == "win":
                ret = (bet.payout - bet.stake) / bet.stake
            else:
                ret = -1.0
            returns.append(ret)

        if not returns:
            return 0.0

        avg_return = sum(returns) / len(returns)

        if len(returns) < 2:
            return 0.0

        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev == 0:
            return 0.0

        return avg_return / std_dev

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage."""
        resolved = self.get_resolved_bets()
        if not resolved:
            return 0.0

        bankroll = self.initial_bankroll
        peak = bankroll
        max_dd = 0.0

        for bet in resolved:
            if bet.result == "win":
                bankroll += bet.payout - bet.stake
            else:
                bankroll -= bet.stake

            if bankroll > peak:
                peak = bankroll

            dd = (peak - bankroll) / peak
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def stats(self) -> dict:
        resolved = self.get_resolved_bets()
        wins = [b for b in resolved if b.result == "win"]
        losses = [b for b in resolved if b.result == "lose"]

        # Realized P&L
        realized_pnl = sum(
            (b.payout - b.stake) if b.result == "win" else -b.stake
            for b in resolved
        )
        total_staked_resolved = sum(b.stake for b in resolved)
        realized_roi = (
            (realized_pnl / self.initial_bankroll * 100)
            if self.initial_bankroll > 0 else 0.0
        )

        roi = (self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100

        underdog_wins = [b for b in resolved if b.result == "win" and b.probability_ai is not None]
        underdog_total = [b for b in resolved if b.probability_ai is not None]

        return {
            "bankroll": round(self.bankroll, 2),
            "initial_bankroll": self.initial_bankroll,
            "roi_pct": round(roi, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_staked_resolved": round(total_staked_resolved, 2),
            "realized_roi": round(realized_roi, 2),
            "total_bets": len(self.bets) + len(resolved),
            "open_bets": len(self.get_open_bets()),
            "resolved_bets": len(resolved),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(resolved) * 100, 1) if resolved else 0,
            "sharpe_ratio": round(self._calculate_sharpe(), 2),
            "max_drawdown": round(self._calculate_max_drawdown() * 100, 1),
            "underdog_hit_rate": round(len(underdog_wins) / len(underdog_total) * 100, 1) if underdog_total else 0,
            "ai_bets": len(underdog_total),
        }

    def to_dict(self) -> dict:
        return {
            **self.stats(),
            "open_bets": [asdict(b) for b in self.get_open_bets()],
            "recent_bets": [asdict(b) for b in self.get_resolved_bets()[-10:]],
        }
