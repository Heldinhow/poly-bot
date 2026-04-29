import logging
import asyncio

from alerts import AlertSender
from client import PolymarketClient
from config import get_settings
from decision import DecisionGate
from filters import build_filter_predicates
from portfolio import PaperPortfolio
from reporter import MarketResolver
from db.cache_repository import CacheRepository
from db.agent_metrics_repository import AgentMetricsRepository
from db.decision_factor_repository import DecisionFactorRepository
from db.execution_summary_repository import ExecutionSummaryRepository
from realtime.events import (
    ExecutionEvent, SCAN_STARTED, MARKET_FILTERED, MARKET_ANALYZING,
    MARKET_ANALYZED, MARKET_DECIDED, BET_RECORDED, PORTFOLIO_RESOLVED,
    SCAN_COMPLETED
)

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
        agent_runner=None,
    ) -> None:
        self._client = client
        self._sender = alert_sender
        self._portfolio = portfolio
        self._resolver = resolver
        self._ai_agents = ai_agents or []
        self._decision_gate = decision_gate
        self._agent_runner = agent_runner
        self._cache = CacheRepository()
        self._factor_repo = DecisionFactorRepository()
        self._summary_repo = ExecutionSummaryRepository()
        self._agent_metrics = AgentMetricsRepository()
        self._event_bus = None

        settings = get_settings()
        self._vol_pred, self._value_pred, self._live_pred = build_filter_predicates(
            settings.min_volume, settings.max_price, settings.max_odds, settings.min_odds
        )
        mode = "AGENT RUNTIME" if agent_runner else "LEGACY"
        logger.info(f"Scanner initialized [{mode} MODE]" + (" [PAPER]" if portfolio else ""))

    def set_event_bus(self, bus):
        self._event_bus = bus

    def _should_analyze(self, market, underdog_price: float, odds: float) -> bool:
        """Check if market should be analyzed using cache + static heuristics.

        Returns True only if:
        - Market passes static filters (odds sweet spot, volume)
        - Market hasn't been analyzed recently with stable price
        """
        try:
            # 1. Odds sweet spot: not too extreme, not too close
            if odds > 10.0 or odds < 2.0:
                return False

            # 2. Implied probability range: underdog between 10% and 40%
            if underdog_price < 0.10 or underdog_price > 0.40:
                return False

            # 3. Volume threshold
            if market.volume_24h < 10000:
                return False

            # 4. Check cache — avoid re-analyzing stable markets
            if not self._cache.should_analyze(
                market.id, market.yes_price, market.no_price
            ):
                logger.debug(f"Cache hit for {market.id}: skipping {market.question[:50]}")
                return False

            return True

        except Exception:
            return False

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

    def scan(self, resolve_only: bool = False) -> int:
        sent = 0
        analyzable = []

        if not resolve_only:
            logger.info("Starting scan...")
            if self._event_bus:
                self._event_bus.publish(ExecutionEvent(
                    type=SCAN_STARTED,
                    message="Scan started",
                    data={"mode": "AGENT RUNTIME" if self._agent_runner else "LEGACY"}
                ))
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
            if self._event_bus:
                self._event_bus.publish(ExecutionEvent(
                    type=MARKET_FILTERED,
                    message=f"Filters: {len(volume_filtered)}/{len(markets)} passed vol, "
                            f"{len(live_filtered)}/{len(volume_filtered)} live, "
                            f"{len(value_bets)}/{len(live_filtered)} value bets",
                    data={"stage": "filters", "volume_filtered": len(volume_filtered),
                          "live_filtered": len(live_filtered), "value_bets": len(value_bets)}
                ))

            # Pre-filter: only analyze markets that pass cache + static checks
            analyzable = []
            for m in value_bets:
                underdog = min(m.yes_price, m.no_price)
                odds = 1.0 / underdog
                if self._should_analyze(m, underdog, odds):
                    analyzable.append(m)

            logger.info(f"Pre-filter: {len(analyzable)}/{len(value_bets)} markets worth analyzing")

            # Create persistent event loop for all AI analysis
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                for market in analyzable:
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

                    if self._event_bus:
                        self._event_bus.publish(ExecutionEvent(
                            type=MARKET_ANALYZING,
                            market_id=market.id,
                            question=market.question,
                            message=f"Analyzing: {market.question[:60]}..."
                        ))

                    # AI Analysis Layer — Agent Runtime first, fallback to legacy agents
                    ai_probability = None
                    ai_analysis = ""
                    agent_name = "unknown"

                    # Try Agent Runtime first
                    if self._agent_runner:
                        try:
                            result = loop.run_until_complete(
                                self._agent_runner.analyze_market(
                                    market_id=market.id,
                                    question=market.question,
                                    yes_price=market.yes_price,
                                    no_price=market.no_price,
                                    volume_24h=market.volume_24h,
                                    resolution_date=getattr(market, 'resolution_date', None),
                                )
                            )
                            if result and result.probability is not None:
                                ai_probability = result.probability
                                ai_analysis = result.reasoning or ""
                                agent_name = getattr(result, 'agent_name', 'AgentRuntime')
                                logger.info(
                                    f"[AgentRuntime] {market.question[:50]}: "
                                    f"agent={agent_name} prob={ai_probability:.2%} | "
                                    f"implied={implied_prob:.2%} | odds={odds:.2f}:1"
                                )
                            elif result and result.error_message:
                                logger.warning(
                                    f"[AgentRuntime] FAILED {market.question[:50]}: {result.error_message}"
                                )
                        except Exception as e:
                            logger.error(f"[AgentRuntime] ERROR {market.question[:50]}: {e}")

                    # Fallback to legacy agents if runtime failed or unavailable
                    if ai_probability is None and self._ai_agents:
                        try:
                            ai_probability, ai_analysis = loop.run_until_complete(
                                self._analyze_market(market)
                            )
                            if ai_probability is not None:
                                agent_name = "LegacyAgents"
                                logger.info(
                                    f"[Legacy] {market.question[:50]}: "
                                    f"prob={ai_probability:.2%} | implied={implied_prob:.2%} | odds={odds:.2f}:1"
                                )
                        except Exception as e:
                            logger.error(f"[Legacy] FAILED {market.question[:50]}: {e}")

                    if self._event_bus and ai_probability is not None:
                        self._event_bus.publish(ExecutionEvent(
                            type=MARKET_ANALYZED,
                            market_id=market.id,
                            question=market.question,
                            message=f"AI prob={ai_probability:.0%} | implied={implied_prob:.0%} | "
                                    f"odds={odds:.1f}x | edge={edge:+.1%}",
                            data={"ai_prob": ai_probability, "implied_prob": implied_prob,
                                  "odds": odds, "edge": edge, "agent": agent_name}
                        ))

                    # Decision Gate
                    decision = "SKIP"
                    reject_reason = None
                    edge = 0.0
                    bet = None
                    if self._decision_gate and ai_probability is not None:
                        edge = (ai_probability * odds) - 1.0
                        decision = self._decision_gate.evaluate_edge(edge, ai_probability, implied_prob)
                        logger.info(
                            f"Decision for {market.question[:50]}: {decision} "
                            f"(edge={edge:+.1%}, ai={ai_probability:.1%}, market={implied_prob:.1%})"
                        )
                        if self._event_bus and decision != "SKIP":
                            self._event_bus.publish(ExecutionEvent(
                                type=MARKET_DECIDED,
                                market_id=market.id,
                                question=market.question,
                                message=f"Decision: {decision} ({reject_reason or 'edge='+str(round(edge,3))})",
                                data={"decision": decision, "edge": edge, "reject_reason": reject_reason}
                            ))
                        if decision == "REJECT":
                            if edge < get_settings().min_edge:
                                reject_reason = "no_edge"
                            elif ai_probability < implied_prob * 0.85:
                                reject_reason = "ai_disagrees"
                            else:
                                reject_reason = "threshold"

                        # Cache the result — must not crash the scan
                        try:
                            self._cache.set_cache(
                                market_id=market.id,
                                question=market.question,
                                yes_price=market.yes_price,
                                no_price=market.no_price,
                                probability=ai_probability,
                                confidence=None,
                                reasoning=ai_analysis,
                                agent_name=agent_name,
                                decision=decision,
                            )
                        except Exception:
                            logger.exception(f"Failed to cache result for {market.id}")

                    # Paper trading: record bet
                    if self._portfolio and decision == "ACCEPT":
                        bet = self._portfolio.record_bet(
                            market_id=market.id,
                            question=market.question,
                            outcome=underdog_outcome,
                            price=underdog_price,
                            probability_ai=ai_probability,
                            analysis_summary=ai_analysis,
                            agent_name=agent_name,
                        )
                        if bet and agent_name:
                            self._agent_metrics.record_bet(agent_name, bet.id)
                        if self._event_bus and bet:
                            self._event_bus.publish(ExecutionEvent(
                                type=BET_RECORDED,
                                market_id=market.id,
                                question=market.question,
                                message=f"Bet recorded: stake=${bet.stake:.2f} @ {odds:.1f}x odds",
                                data={"stake": bet.stake, "odds": odds, "kelly_frac": bet.kelly_frac}
                            ))

                    # Persist decision factors and execution summary
                    try:
                        first_exec_id = None
                        last_exec_id = None
                        if (result and hasattr(result, 'execution_log_id') and result.execution_log_id):
                            last_exec_id = result.execution_log_id
                            first_exec_id = result.execution_log_id

                        self._factor_repo.create(
                            execution_log_id=last_exec_id,
                            market_id=market.id,
                            implied_prob=implied_prob,
                            ai_prob=ai_probability or 0.0,
                            odds=odds,
                            edge=edge,
                            decision=decision,
                            reject_reason=reject_reason,
                            bet_id=getattr(bet, 'id', None) if bet else None,
                            stake=getattr(bet, 'stake', None) if bet else None,
                            kelly_frac=getattr(bet, 'kelly_frac', None) if bet else None,
                        )
                        self._summary_repo.upsert_from_market(
                            market_id=market.id,
                            question=market.question,
                            yes_price=market.yes_price,
                            no_price=market.no_price,
                            volume_24h=market.volume_24h,
                            resolution_date=getattr(market, 'resolution_date', None) or "",
                            agent_names=[agent_name],
                            probabilities=[ai_probability] if ai_probability else [],
                            confidences=[],
                            reasoning_summary=ai_analysis[:500] if ai_analysis else "",
                            decision=decision,
                            reject_reason=reject_reason or "",
                            edge=edge,
                            first_execution_id=first_exec_id,
                            last_execution_id=last_exec_id,
                            execution_count=1,
                        )
                        if bet:
                            self._summary_repo.update_bet_link(
                                market_id=market.id,
                                bet_id=bet.id,
                                stake=bet.stake,
                                outcome=underdog_outcome,
                            )
                    except Exception as e:
                        logger.error(f"Failed to write audit trail for {market.id}: {e}")

                    if decision == "REJECT":
                        logger.info(f"Skipping {market.question[:50]} — no value edge")

                    # Paper trading: record bet and send alert
                    if self._portfolio and decision == "ACCEPT" and bet:
                        sent += 1 if self._sender.send_paper_bet(
                            market, bet, self._portfolio.bankroll,
                            probability_ai=ai_probability,
                            analysis_summary=ai_analysis
                        ) else 0
                    elif not self._portfolio:
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

        # Check resolutions for paper portfolio — always runs, even in resolve_only mode
        if self._portfolio and self._resolver:
            resolved = self._resolver.resolve_portfolio(self._portfolio)
            stats = self._portfolio.stats()
            logger.info(
                f"Portfolio: bankroll=${stats['bankroll']:.2f} "
                f"ROI={stats['roi_pct']:.1f}% "
                f"({stats['wins']}W/{stats['losses']}L)"
            )
            if self._event_bus and stats:
                self._event_bus.publish(ExecutionEvent(
                    type=PORTFOLIO_RESOLVED,
                    message=f"Portfolio: bankroll=${stats['bankroll']:.2f} | "
                            f"ROI={stats['roi_pct']:.1f}% | {stats['wins']}W/{stats['losses']}L",
                    data={"bankroll": stats['bankroll'], "roi_pct": stats['roi_pct'],
                          "wins": stats['wins'], "losses": stats['losses'],
                          "resolved": resolved}
                ))
            if resolved:
                self._sender.send_portfolio_update(stats)

        if self._event_bus:
            self._event_bus.publish(ExecutionEvent(
                type=SCAN_COMPLETED,
                message=f"Scan complete — analyzed: {len(analyzable)}, bets: {sent}",
                data={"markets_analyzed": len(analyzable), "bets_placed": sent}
            ))
        logger.info(f"Scan complete. Alerts sent: {sent}")
        return sent
