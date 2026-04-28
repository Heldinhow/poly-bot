import logging
import time
import sys

from client import PolymarketClient
from config import get_settings
from scanner import Scanner
from alerts import AlertSender
from portfolio import PaperPortfolio
from reporter import MarketResolver
from decision import DecisionGate
from agents import create_default_agents
from db.connection import init_schema, health_check
from db.repository import BetRepository
from trading.mode_gate import TradingModeGate


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Polymarket Merge — Underdog + AI Orchestration")
    logger.info("=" * 60)

    settings = get_settings()

    # Database health check and schema initialization
    logger.info("Connecting to PostgreSQL...")
    if not health_check():
        logger.error("PostgreSQL is not reachable. Check DATABASE_URL and ensure the DB is running.")
        sys.exit(1)
    init_schema()
    logger.info("Database schema initialized")

    # Trading mode
    mode_gate = TradingModeGate()
    logger.info(f"Trading mode: {mode_gate.get_current_mode().upper()}")
    if settings.paper_mode != (mode_gate.get_current_mode() == "paper"):
        logger.warning("Legacy paper_mode setting differs from trading_mode — using trading_mode")

    logger.info(f"Bankroll: ${settings.initial_bankroll:.2f}")
    logger.info(f"Kelly fraction: {settings.kelly_frac:.0%}")
    logger.info(f"Scan interval: {settings.scan_interval_secs}s")
    logger.info(f"AI agents: 3 (Sports, Esports, Odds)")
    logger.info(f"Decision thresholds: HIGH > {settings.high_confidence_threshold:.0%}, LOW < {settings.low_confidence_threshold:.0%}")

    client = PolymarketClient()
    alert_sender = AlertSender(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    repository = BetRepository()
    portfolio = PaperPortfolio(
        repository=repository,
        mode_gate=mode_gate,
        initial_bankroll=settings.initial_bankroll,
        kelly_frac=settings.kelly_frac,
        min_edge=settings.min_edge,
    )
    resolver = MarketResolver(http_client=client._http)
    decision_gate = DecisionGate()
    ai_agents = create_default_agents()

    scanner = Scanner(
        client=client,
        alert_sender=alert_sender,
        portfolio=portfolio,
        resolver=resolver,
        ai_agents=ai_agents,
        decision_gate=decision_gate,
    )

    logger.info("Starting main loop...")
    cycle = 0

    try:
        while True:
            cycle += 1
            logger.info(f"--- Cycle {cycle} ---")

            try:
                scanner.scan()
            except Exception as e:
                logger.error(f"Scan failed: {e}")

            logger.info(f"Sleeping for {settings.scan_interval_secs}s...")
            time.sleep(settings.scan_interval_secs)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        client.close()
        logger.info("Client closed. Goodbye!")


if __name__ == "__main__":
    main()
