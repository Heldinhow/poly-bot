"""Unit tests for portfolio P&L calculation logic.

Tests the core invariants WITHOUT requiring DB dependencies:
1. Only resolved bets affect realized P&L
2. Open bets have ZERO impact on the chart/realized metrics
3. Chart final value == total_realized_pnl
4. WIN: payout - stake, LOSS: -stake
5. ROI = realized_pnl / total_staked_resolved
"""
from datetime import datetime, timezone


def make_bet_dict(
    market_id: str,
    stake: float,
    payout: float,
    price: float,
    result: str | None,
    resolved: bool,
    timestamp: str,
    resolved_at: str | None,
    probability_ai: float | None = None,
) -> dict:
    """Factory to create Bet-like dict fixtures (no ORM dependency)."""
    return {
        "market_id": market_id,
        "question": f"Question {market_id}",
        "outcome": "YES",
        "price": price,
        "stake": stake,
        "payout": payout,
        "kelly_frac": 0.1,
        "edge": 0.05,
        "timestamp": timestamp,
        "resolved": resolved,
        "result": result,
        "resolved_at": resolved_at,
        "probability_ai": probability_ai,
    }


# ---------------------------------------------------------------------------
# Pure P&L calculation functions (mirror what the API uses)
# ---------------------------------------------------------------------------

def realized_pnl(bet: dict) -> float:
    """Single bet realized P&L: WIN→payout-stake, LOSS→-stake."""
    if bet["result"] == "win":
        return bet["payout"] - bet["stake"]
    else:
        return -bet["stake"]


def accumulate_realized(bets: list[dict]) -> list[dict]:
    """Build cumulative realized P&L series from resolved bets sorted by resolved_at."""
    resolved = [b for b in bets if b.get("resolved") and b.get("resolved_at")]
    resolved.sort(key=lambda b: b["resolved_at"])

    cumulative = 0.0
    result = []
    for b in resolved:
        cumulative += realized_pnl(b)
        result.append({
            "date": b["resolved_at"][:10],
            "realized_pnl": round(cumulative, 2),
        })
    return result


def compute_realized_stats(bets: list[dict]) -> dict:
    """Compute total realized P&L and ROI from resolved bets."""
    resolved = [b for b in bets if b.get("resolved")]
    wins = [b for b in resolved if b.get("result") == "win"]
    losses = [b for b in resolved if b.get("result") == "lose"]

    realized_pnl_total = sum(realized_pnl(b) for b in resolved)
    total_staked = sum(b["stake"] for b in resolved)
    realized_roi = (realized_pnl_total / total_staked * 100) if total_staked > 0 else 0.0

    return {
        "realized_pnl": round(realized_pnl_total, 2),
        "total_staked_resolved": round(total_staked, 2),
        "realized_roi": round(realized_roi, 2),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(resolved) * 100, 1) if resolved else 0,
    }


# ---------------------------------------------------------------------------
# Tests: P&L per bet type
# ---------------------------------------------------------------------------

class TestRealizedPnL:
    def test_win_pnl_is_payout_minus_stake(self):
        bet = make_bet_dict(
            market_id="m1", stake=10.0, payout=20.0, price=0.5,
            result="win", resolved=True,
            timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
        )
        assert realized_pnl(bet) == 10.0  # 20 - 10

    def test_loss_pnl_is_minus_stake(self):
        bet = make_bet_dict(
            market_id="m1", stake=10.0, payout=0.0, price=0.5,
            result="lose", resolved=True,
            timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
        )
        assert realized_pnl(bet) == -10.0


# ---------------------------------------------------------------------------
# Tests: Open bets have ZERO impact
# ---------------------------------------------------------------------------

class TestOpenBetsHaveNoImpact:
    def test_open_bet_excluded_from_resolved_filter(self):
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result=None, resolved=False,
                timestamp="2024-01-01T00:00:00Z", resolved_at=None,
            ),
            make_bet_dict(
                market_id="m2", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
        ]
        resolved = [b for b in bets if b.get("resolved") and b.get("resolved_at")]
        assert len(resolved) == 1
        assert resolved[0]["market_id"] == "m2"

    def test_open_bet_does_not_distort_series(self):
        """Open bets present → no impact on cumulative chart."""
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m2", stake=50.0, payout=0.0, price=0.5,
                result=None, resolved=False,
                timestamp="2024-01-03T00:00:00Z", resolved_at=None,
            ),
        ]
        series = accumulate_realized(bets)
        assert len(series) == 1
        assert series[0]["realized_pnl"] == 10.0  # open bet stake ignored


# ---------------------------------------------------------------------------
# Tests: Timeseries accumulation
# ---------------------------------------------------------------------------

class TestTimeseriesLogic:
    def test_only_wins_strictly_increasing(self):
        bets = [
            make_bet_dict(
                market_id=f"m{i}", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z",
                resolved_at=f"2024-01-0{i+1}T00:00:00Z",
            )
            for i in range(1, 4)
        ]
        series = accumulate_realized(bets)
        assert len(series) == 3
        assert series[0]["realized_pnl"] == 10.0
        assert series[1]["realized_pnl"] == 20.0
        assert series[2]["realized_pnl"] == 30.0

    def test_mixed_results_step_like(self):
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m2", stake=10.0, payout=0.0, price=0.5,
                result="lose", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-03T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m3", stake=10.0, payout=30.0, price=0.33,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-04T00:00:00Z",
            ),
        ]
        series = accumulate_realized(bets)
        assert [s["realized_pnl"] for s in series] == [10.0, 0.0, 20.0]

    def test_no_resolved_bets_returns_empty(self):
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=0.0, price=0.5,
                result=None, resolved=False,
                timestamp="2024-01-01T00:00:00Z", resolved_at=None,
            )
        ]
        series = accumulate_realized(bets)
        assert series == []


# ---------------------------------------------------------------------------
# Tests: ROI calculation
# ---------------------------------------------------------------------------

class TestROI:
    def test_roi_zero_when_break_even(self):
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m2", stake=10.0, payout=0.0, price=0.5,
                result="lose", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-03T00:00:00Z",
            ),
        ]
        stats = compute_realized_stats(bets)
        assert stats["realized_pnl"] == 0.0
        assert stats["realized_roi"] == 0.0

    def test_roi_100_percent(self):
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m2", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-03T00:00:00Z",
            ),
        ]
        stats = compute_realized_stats(bets)
        assert stats["realized_pnl"] == 20.0   # +10 + 10
        assert stats["realized_roi"] == 100.0  # 20/20 * 100

    def test_chart_final_value_equals_total_realized_pnl(self):
        """Critical invariant: chart last value == total realized P&L."""
        bets = [
            make_bet_dict(
                market_id="m1", stake=10.0, payout=20.0, price=0.5,
                result="win", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-02T00:00:00Z",
            ),
            make_bet_dict(
                market_id="m2", stake=10.0, payout=0.0, price=0.5,
                result="lose", resolved=True,
                timestamp="2024-01-01T00:00:00Z", resolved_at="2024-01-03T00:00:00Z",
            ),
        ]
        series = accumulate_realized(bets)
        stats = compute_realized_stats(bets)
        chart_final = series[-1]["realized_pnl"] if series else 0.0
        assert chart_final == stats["realized_pnl"], (
            f"Chart final value ({chart_final}) must equal total realized P&L ({stats['realized_pnl']})"
        )
