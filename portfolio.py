import csv
import logging
import math
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PaperBet:
    market_id: str
    question: str
    outcome: str
    price: float
    stake: float
    payout: float
    kelly_frac: float
    edge: float
    timestamp: str
    probability_ai: Optional[float] = None
    analysis_summary: str = ""
    resolved: bool = False
    result: Optional[str] = None
    resolved_at: Optional[str] = None

    def to_row(self) -> dict:
        return {
            "market_id": self.market_id,
            "question": self.question,
            "outcome": self.outcome,
            "price": f"{self.price:.4f}",
            "stake": f"{self.stake:.2f}",
            "payout": f"{self.payout:.2f}",
            "kelly_frac": f"{self.kelly_frac:.2f}",
            "edge": f"{self.edge:.1%}",
            "timestamp": self.timestamp,
            "probability_ai": f"{self.probability_ai:.4f}" if self.probability_ai is not None else "",
            "analysis_summary": self.analysis_summary or "",
            "resolved": str(self.resolved),
            "result": self.result or "",
            "resolved_at": self.resolved_at or "",
        }


class PaperPortfolio:
    def __init__(
        self,
        initial_bankroll: float,
        kelly_frac: float,
        min_edge: float,
        csv_path: str = "paper_trades.csv",
    ):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.kelly_frac = kelly_frac
        self.min_edge = min_edge
        self.csv_path = Path(csv_path)
        self.bets: list[PaperBet] = []
        self._load_csv()
        logger.info(
            f"PaperPortfolio: bankroll=${self.bankroll:.2f}, Kelly={kelly_frac:.0%}, min_edge={min_edge:.0%}"
        )

    def _load_csv(self) -> None:
        if not self.csv_path.exists():
            return
        try:
            with open(self.csv_path, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bet = PaperBet(
                        market_id=row["market_id"],
                        question=row["question"],
                        outcome=row["outcome"],
                        price=float(row["price"]),
                        stake=float(row["stake"]),
                        payout=float(row["payout"]),
                        kelly_frac=float(row["kelly_frac"]),
                        edge=float(row["edge"].replace("%", "")) / 100,
                        timestamp=row["timestamp"],
                        probability_ai=float(row["probability_ai"]) if row.get("probability_ai") else None,
                        analysis_summary=row.get("analysis_summary", ""),
                        resolved=row["resolved"] == "True",
                        result=row["result"] if row["result"] else None,
                        resolved_at=row["resolved_at"] if row["resolved_at"] else None,
                    )
                    self.bets.append(bet)
                    if bet.resolved and bet.result == "win":
                        self.bankroll += float(row["payout"]) - float(row["stake"])
        except Exception as e:
            logger.warning(f"Failed to load CSV: {e}")

    def _save_csv(self) -> None:
        if not self.bets:
            return
        with open(self.csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.bets[0].to_row().keys()))
            writer.writeheader()
            for bet in self.bets:
                writer.writerow(bet.to_row())

    def _kelly_stake(self, odds: float, probability_ai: Optional[float] = None) -> tuple[float, float]:
        """
        Kelly: stake = frac * (b*p - q) / b.
        If probability_ai is provided, use it instead of 1.0.
        """
        b = odds - 1
        if b <= 0:
            return 0.0, 0.0
        
        # Use AI probability if available, otherwise default to implied probability
        p = probability_ai if probability_ai is not None else 1.0 / odds
        q = 1.0 - p
        
        # Edge calculation
        edge = (p * odds) - 1
        if edge <= self.min_edge:
            return 0.0, edge
        
        kelly_pct = self.kelly_frac * (b * p - q) / b
        stake = kelly_pct * self.bankroll
        stake = max(stake, 1.00)  # Polymarket minimum per trade
        return stake, edge

    def record_bet(
        self,
        market_id: str,
        question: str,
        outcome: str,
        price: float,
        probability_ai: Optional[float] = None,
        analysis_summary: str = "",
    ) -> Optional[PaperBet]:
        if any(b.market_id == market_id and not b.resolved for b in self.bets):
            return None

        payout_odds = 1.0 / price
        stake, edge = self._kelly_stake(payout_odds, probability_ai)
        if stake <= 0:
            return None

        stake = min(stake, self.bankroll * 0.1)
        payout = stake * payout_odds
        now = datetime.now(timezone.utc).isoformat()

        bet = PaperBet(
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
        )
        self.bets.append(bet)
        self.bankroll -= stake
        self._save_csv()
        logger.info(
            f"Paper bet: {question[:50]} | ${stake:.2f} @ {price*100:.1f}% "
            f"| payout=${payout:.2f} | bankroll=${self.bankroll:.2f}"
            f"{' | AI prob=' + f'{probability_ai:.1%}' if probability_ai else ''}"
        )
        return bet

    def resolve_bet(self, market_id: str, won: bool) -> None:
        for bet in self.bets:
            if bet.market_id == market_id and not bet.resolved:
                bet.resolved = True
                bet.result = "win" if won else "lose"
                bet.resolved_at = datetime.now(timezone.utc).isoformat()
                if won:
                    self.bankroll += bet.payout
                self._save_csv()
                logger.info(
                    f"Bet resolved: {bet.question[:50]} | {bet.result} "
                    f"| bankroll=${self.bankroll:.2f}"
                )
                return

    def get_open_bets(self) -> list[PaperBet]:
        return [b for b in self.bets if not b.resolved]

    def get_resolved_bets(self) -> list[PaperBet]:
        return [b for b in self.bets if b.resolved]

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
        
        # Track bankroll over time
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
        roi = (self.bankroll - self.initial_bankroll) / self.initial_bankroll * 100
        
        # Underdog specific stats
        underdog_wins = [b for b in resolved if b.result == "win" and b.probability_ai is not None]
        underdog_total = [b for b in resolved if b.probability_ai is not None]
        
        return {
            "bankroll": round(self.bankroll, 2),
            "initial_bankroll": self.initial_bankroll,
            "roi_pct": round(roi, 2),
            "total_bets": len(self.bets),
            "open_bets": len(self.get_open_bets()),
            "resolved_bets": len(resolved),
            "wins": len(wins),
            "losses": len(resolved) - len(wins),
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
