from datetime import datetime, timezone
from typing import Callable

from client import Market

# Keywords that indicate a future prediction (NOT live/in-play)
PREDICTION_EXCLUDE_KW = [
    " 2026", " 2027", " 2028", " 2029", " 2030",
    "president", "election", "democratic", "republican", "congress", "senate",
    "parliament", "governor", "mayor", "polling", "nomination",
    "world cup 202", "euro 202", "champions league 202", "stanley cup 202",
    " fifa world", "olympic", "presidential",
    " by ", "before ", "after ", "between ", "by end of", "by april", "by may",
    "by june", "by july", "by august", "by september", "by october", "by november", "by december",
    "before april", "before may", "before june", "before july",
]

FINANCIAL_EXCLUDE_KW = [
    "bitcoin", "btc", "ether", "ethereum", "crypto", "gold", "oil price",
    "stock", "nasdaq", "sp 500", "s&p", "dow jones", "market cap",
    "announce", "purchase april", "dip to", "reach $", "above $",
]

LIVE_INCLUDE_KW = [
    " vs ", " @ ", " vs. ", " - ",
]

MAX_RESOLUTION_HOURS = 48


def is_live_friendly_predicate(market: Market) -> bool:
    try:
        q = market.question.lower()

        has_pred_kw = any(kw.lower() in q for kw in PREDICTION_EXCLUDE_KW)
        if has_pred_kw:
            return False

        has_fin_kw = any(kw.lower() in q for kw in FINANCIAL_EXCLUDE_KW)
        if has_fin_kw:
            return False

        if not market.resolution_date:
            return False

        try:
            res_date = market.resolution_date
            if isinstance(res_date, str):
                res_date = datetime.fromisoformat(res_date.replace("Z", "+00:00"))
            if res_date.tzinfo is None:
                res_date = res_date.replace(tzinfo=timezone.utc)
        except Exception:
            return False

        now = datetime.now(timezone.utc)

        if res_date < now:
            return False

        hours_until = (res_date - now).total_seconds() / 3600

        if hours_until <= MAX_RESOLUTION_HOURS:
            return True

        return False

    except Exception:
        return False


def active_volume_predicate(min_volume: float) -> Callable[[Market], bool]:
    def predicate(market: Market) -> bool:
        try:
            if len(market.outcomes) != 2:
                return False
            if market.yes_price is None or market.no_price is None:
                return False
            if market.volume_24h < min_volume:
                return False
            return True
        except Exception:
            return False

    return predicate


def value_bet_underdog_predicate(max_price: float, max_odds: float = 20.0) -> Callable[[Market], bool]:
    def predicate(market: Market) -> bool:
        try:
            yes_price = market.yes_price
            no_price = market.no_price

            if yes_price is None or no_price is None:
                return False

            res_date = market.resolution_date
            if res_date:
                try:
                    if isinstance(res_date, str):
                        res_date = datetime.fromisoformat(res_date.replace("Z", "+00:00"))
                    if res_date.tzinfo is None:
                        res_date = res_date.replace(tzinfo=timezone.utc)
                    if res_date < datetime.now(timezone.utc):
                        return False
                except Exception:
                    pass

            if yes_price < no_price:
                underdog_price = yes_price
                favorite_price = no_price
            else:
                underdog_price = no_price
                favorite_price = yes_price

            if underdog_price > max_price:
                return False

            odds = 1 / underdog_price

            if odds > max_odds:
                return False

            gap = favorite_price - underdog_price
            if gap < 0.05:
                return False

            return True
        except Exception:
            return False

    return predicate


def build_filter_predicates(min_volume: float, max_price: float, max_odds: float):
    vol_pred = active_volume_predicate(min_volume)
    value_pred = value_bet_underdog_predicate(max_price, max_odds)
    return vol_pred, value_pred, is_live_friendly_predicate
