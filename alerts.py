import asyncio
import logging
from typing import Optional, Set

from telegram import Bot

from client import Market
from portfolio import PaperBet

logger = logging.getLogger(__name__)


class AlertSender:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot = Bot(token=bot_token)
        self._chat_id = chat_id
        self._sent_ids: Set[str] = set()
        self._paper_sent_ids: Set[str] = set()
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        logger.info("AlertSender initialized")

    def _is_duplicate(self, market_id: str) -> bool:
        return market_id in self._sent_ids

    def _mark_sent(self, market_id: str) -> None:
        self._sent_ids.add(market_id)

    def _base_message(
        self, market: Market, underdog_price: float, underdog_outcome: str,
        favorite_price: float, favorite_outcome: str
    ) -> str:
        odds = 1 / underdog_price
        return (
            f"🎯 <b>VALUE BET ENCONTRADO</b>\n\n"
            f"<b>{market.question}</b>\n\n"
            f"🐕 Underdog: <code>{underdog_outcome}</code> @ <b>{underdog_price * 100:.1f}%</b> → payout <b>{odds:.2f}:1</b>\n"
            f"⭐ Favorite: <code>{favorite_outcome}</code> @ {favorite_price * 100:.1f}%\n"
            f"📊 Vol 24h: <code>${market.volume_24h:,.0f}</code> | Liq: <code>${market.liquidity:,.0f}</code>\n\n"
            f"🔗 <a href='{market.url}'>Ver mercado</a>"
        )

    def send(self, market: Market) -> bool:
        try:
            if self._is_duplicate(market.id):
                return False

            yes_price, no_price = market.yes_price, market.no_price
            if yes_price is None or no_price is None:
                return False

            if yes_price < no_price:
                underdog_price, underdog_outcome = yes_price, market.outcomes[0].outcome
                favorite_price, favorite_outcome = no_price, market.outcomes[1].outcome
            else:
                underdog_price, underdog_outcome = no_price, market.outcomes[1].outcome
                favorite_price, favorite_outcome = yes_price, market.outcomes[0].outcome

            text = self._base_message(market, underdog_price, underdog_outcome, favorite_price, favorite_outcome)

            self._loop.run_until_complete(
                self._bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            )
            self._mark_sent(market.id)
            logger.info(f"Alert sent: {market.question[:50]}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False

    def send_paper_bet(
        self,
        market: Market,
        bet: PaperBet,
        bankroll: float,
        probability_ai: Optional[float] = None,
        analysis_summary: str = "",
    ) -> bool:
        try:
            if bet.market_id in self._paper_sent_ids:
                return False

            odds = 1 / bet.price
            edge_pct = bet.edge * 100
            
            # Build AI analysis section
            ai_section = ""
            if probability_ai is not None:
                ai_section = (
                    f"\n🤖 <b>Análise IA</b>\n"
                    f"Probabilidade estimada: <b>{probability_ai:.1%}</b>\n"
                )
                if analysis_summary:
                    # Truncate analysis to fit in message
                    summary = analysis_summary[:200] + "..." if len(analysis_summary) > 200 else analysis_summary
                    ai_section += f"Resumo: <i>{summary}</i>\n"

            text = (
                f"📝 <b>PAPER BET REGISTADA</b>{' ✅ HIGH CONVICTION' if probability_ai and probability_ai >= 0.6 else ''}\n\n"
                f"<b>{market.question}</b>\n\n"
                f"🐕 Aposta: <code>{bet.outcome}</code> @ <b>{bet.price * 100:.1f}%</b>\n"
                f"💰 Stake: <code>${bet.stake:.2f}</code> | Payout: <code>${bet.payout:.2f}</code>\n"
                f"📈 Edge: <b>+{edge_pct:.0f}%</b> | Kelly: <code>{bet.kelly_frac:.0%}</code>\n"
                f"💳 Bankroll disponível: <code>${bankroll:.2f}</code>"
                f"{ai_section}\n"
                f"🔗 <a href='{market.url}'>Ver mercado</a>"
            )

            self._loop.run_until_complete(
                self._bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            )
            self._paper_sent_ids.add(bet.market_id)
            self._mark_sent(market.id)
            logger.info(f"Paper bet alert: {market.question[:50]}")
            return True

        except Exception as e:
            logger.error(f"Failed to send paper bet alert: {e}")
            return False

    def send_portfolio_update(self, stats: dict) -> bool:
        try:
            roi = stats["roi_pct"]
            roi_emoji = "📈" if roi >= 0 else "📉"
            roi_color = "+" if roi >= 0 else ""

            # Add AI-specific metrics if available
            ai_section = ""
            if "sharpe_ratio" in stats:
                ai_section += f"📊 Sharpe: {stats['sharpe_ratio']:.2f}\n"
            if "max_drawdown" in stats:
                ai_section += f"📉 Max Drawdown: {stats['max_drawdown']:.1f}%\n"
            if "underdog_hit_rate" in stats and stats["ai_bets"] > 0:
                ai_section += f"🎯 Underdog Hit Rate: {stats['underdog_hit_rate']:.0f}% ({stats['ai_bets']} bets)\n"

            text = (
                f"{roi_emoji} <b>PORTFOLIO UPDATE</b>\n\n"
                f"💰 Bankroll: <code>${stats['bankroll']:.2f}</code> "
                f"({roi_color}{roi:.1f}% ROI)\n"
                f"🎲 Bets: {stats['total_bets']} total | "
                f"{stats['open_bets']} abertas | {stats['resolved_bets']} resolvidas\n"
                f"✅ Win rate: {stats['win_rate']:.0f}% "
                f"({stats['wins']}W / {stats['losses']}L)\n"
                f"{ai_section}"
            )

            self._loop.run_until_complete(
                self._bot.send_message(
                    chat_id=self._chat_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send portfolio update: {e}")
            return False

    def _get_bankroll_estimate(self) -> float:
        return 0.0
