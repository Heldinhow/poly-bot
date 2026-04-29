import csv
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Bet:
    """Bet model for both paper and live trading."""

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
    trading_mode: str = "paper"
    agent_name: Optional[str] = None
    source: str = "scan"
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialize for API JSON responses."""
        return {
            "id": self.id,
            "market_id": self.market_id,
            "question": self.question,
            "outcome": self.outcome,
            "price": self.price,
            "stake": self.stake,
            "payout": self.payout,
            "kelly_frac": self.kelly_frac,
            "edge": self.edge,
            "probability_ai": self.probability_ai,
            "analysis_summary": self.analysis_summary,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "result": self.result,
            "resolved_at": self.resolved_at,
            "trading_mode": self.trading_mode,
            "agent_name": self.agent_name,
        }

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
            "trading_mode": self.trading_mode,
            "agent_name": self.agent_name,
            "source": self.source,
        }

    def to_db_dict(self) -> dict:
        """Serialize for database insertion."""
        return {
            "market_id": self.market_id,
            "question": self.question,
            "outcome": self.outcome,
            "price": self.price,
            "stake": self.stake,
            "payout": self.payout,
            "kelly_frac": self.kelly_frac,
            "edge": self.edge,
            "timestamp": self.timestamp,
            "probability_ai": self.probability_ai,
            "analysis_summary": self.analysis_summary or None,
            "resolved": self.resolved,
            "result": self.result,
            "resolved_at": self.resolved_at,
            "trading_mode": self.trading_mode,
            "agent_name": self.agent_name,
            "source": self.source,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Bet":
        """Create Bet from a database row (RealDictCursor)."""
        return cls(
            market_id=row["market_id"],
            question=row["question"],
            outcome=row["outcome"],
            price=float(row["price"]),
            stake=float(row["stake"]),
            payout=float(row["payout"]),
            kelly_frac=float(row["kelly_frac"]),
            edge=float(row["edge"]),
            timestamp=row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else row["timestamp"],
            probability_ai=float(row["probability_ai"]) if row.get("probability_ai") is not None else None,
            analysis_summary=row.get("analysis_summary") or "",
            resolved=row["resolved"],
            result=row.get("result"),
            resolved_at=row["resolved_at"].isoformat() if isinstance(row.get("resolved_at"), datetime) else row.get("resolved_at"),
            trading_mode=row["trading_mode"],
            agent_name=row.get("agent_name"),
            source=row.get("source", "scan"),
            id=row.get("id"),
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "Bet":
        """Create Bet from a CSV row (legacy migration)."""
        return cls(
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
            resolved=row.get("resolved", "").lower() == "true",
            result=row["result"] if row.get("result") else None,
            resolved_at=row["resolved_at"] if row.get("resolved_at") else None,
            trading_mode="paper",
        )
