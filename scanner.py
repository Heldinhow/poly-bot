import logging
import asyncio

from alerts import AlertSender
from client import PolymarketClient
from config import get_settings
from decision import DecisionGate
from filters import build_filter_predicates
from portfolio import PaperPortfolio
from reporter import MarketResolver

logger = logging.getLogger(__name__)


class Scanner:
    def __init__(
        self,
        client: PolymarketClient,
        alert_sender: AlertSender,
        portfolio: PaperPortfolio | None = None,
        resolver: MarketResolver | None = None,
        ai_agents: list | None = None,
        decision_gate: DecisionGate | None = None,
    ) -> None:
        self._client = client
        self._sender = alert_sender
        self._portfolio = portfolio
        self._resolver = resolver
        self._ai_agents = ai_agents or []
        self._decision_gate = decision_gate
        
        settings = get_settings()
        self._vol_pred, self._value_pred, self._live_pred = build_filter_predicates(
            settings.min_volume, settings.max_price, settings.max_odds
        )
        logger.info("Scanner initialized" + (" [PAPER MODE]" if portfolio else ""))

    async def _analyze_market(self, market) -> tuple[float | None, str]:
        """Run all AI agents for a single market concurrently."""
        if not self._ai_agents:
            return None, ""
        
        async def run_agent(agent):
            try:
                result = await agent.analyze(market)
                if result and "probability" in result:
                    return result
            except Exception as e:
                logger.warning(f"Agent {agent.name} failed: {e}")
            return None
        
        # Run all agents concurrently
        results = await asyncio.gather(*[run_agent(a) for a in self._ai_agents])
        
        probabilities = []
        analyses = []
        for agent, result in zip(self._ai_agents, results):
            if result and "probability" in result:
                probabilities.append(result["probability"])
                if "reasoning" in result:
                    analyses.append(f"{agent.name}: {result['reasoning']}")
        
        if probabilities:
            avg_prob = sum(probabilities) / len(probabilities)
            summary = " | ".join(analyses)
            return avg_prob, summary
        
        return None, ""

    def scan(self) -> int:
        logger.info("Starting scan...")
        markets = self._client.fetch_active_markets(limit=200)
        if not markets:
            logger.warning("No markets fetched")
            return 0

        volume_filtered = self._client.filter_markets(markets, self._vol_pred)
        logger.debug(f"Stage 1: {len(volume_filtered)}/{len(markets)} markets")

        live_filtered = self._client.filter_markets(volume_filtered, self._live_pred)
        logger.debug(f"Stage 2 (live): {len(live_filtered)}/{len(volume_filtered)} markets")

        value_bets = self._client.filter_markets(live_filtered, self._value_pred)
        logger.info(f"Found {len(value_bets)} value bet opportunities")

        sent = 0
        
        # Create persistent event loop for all AI analysis
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            for market in value_bets:
                underdog_price = (
                    market.yes_price
                    if market.yes_price < market.no_price
                    else market.no_price
                )
                underdog_outcome = (
                    market.outcomes[0].outcome
                    if market.yes_price < market.no_price
                    else market.outcomes[1].outcome
                )
                odds = 1.0 / underdog_price
                implied_prob = underdog_price

                # AI Analysis Layer — run within persistent loop
                ai_probability = None
                ai_analysis = ""
                if self._ai_agents:
                    try:
                        ai_probability, ai_analysis = loop.run_until_complete(
                            self._analyze_market(market)
                        )
                        if ai_probability is not None:
                            logger.info(
                                f"AI analysis for {market.question[:50]}: "
                                f"ai_prob={ai_probability:.2%} | implied={implied_prob:.2%} | odds={odds:.2f}:1"
                            )
                    except Exception as e:
                        logger.error(f"AI analysis failed for {market.question[:50]}: {e}")

                # Decision Gate
                if self._decision_gate and ai_probability is not None:
                    edge = (ai_probability * odds) - 1.0
                    decision = self._decision_gate.evaluate_edge(edge, ai_probability, implied_prob)
                    logger.info(
                        f"Decision for {market.question[:50]}: {decision} "
                        f"(edge={edge:+.1%}, ai={ai_probability:.1%}, market={implied_prob:.1%})"
                    )
                    if decision == "REJECT":
                        logger.info(f"Skipping {market.question[:50]} — no value edge")
                        continue

                # Paper trading: record bet
                bet = None
                if self._portfolio:
                    bet = self._portfolio.record_bet(
                        market_id=market.id,
                        question=market.question,
                        outcome=underdog_outcome,
                        price=underdog_price,
                        probability_ai=ai_probability,
                        analysis_summary=ai_analysis,
                    )
                    if bet:
                        sent += 1 if self._sender.send_paper_bet(
                            market, bet, self._portfolio.bankroll,
                            probability_ai=ai_probability,
                            analysis_summary=ai_analysis
                        ) else 0
                else:
                    sent += 1 if self._sender.send(market) else 0
        finally:
            # Clean up: close all agent clients and the loop
            if self._ai_agents:
                for agent in self._ai_agents:
                    if agent._llm_client:
                        try:
                            loop.run_until_complete(agent._llm_client.close())
                        except Exception:
                            pass
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception:
                pass

        # Check resolutions for paper portfolio
        if self._portfolio and self._resolver:
            resolved = self._resolver.resolve_portfolio(self._portfolio)
            stats = self._portfolio.stats()
            logger.info(
                f"Portfolio: bankroll=${stats['bankroll']:.2f} "
                f"ROI={stats['roi_pct']:.1f}% "
                f"({stats['wins']}W/{stats['losses']}L)"
            )
            if resolved:
                self._sender.send_portfolio_update(stats)

        logger.info(f"Scan complete. Alerts sent: {sent}")
        return sent
