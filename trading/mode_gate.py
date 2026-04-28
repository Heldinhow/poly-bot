import logging
from config import get_settings

logger = logging.getLogger(__name__)


class TradingModeGate:
    """Enforces trading mode decisions and prevents accidental live execution."""

    def __init__(self):
        settings = get_settings()
        self._mode = settings.trading_mode
        logger.info(f"TradingModeGate initialized — mode: {self._mode.upper()}")

    def get_current_mode(self) -> str:
        """Return current trading mode: 'paper' or 'live'."""
        return self._mode

    def is_live_enabled(self) -> bool:
        """Return True if live trading mode is active."""
        return self._mode == "live"

    def is_paper_mode(self) -> bool:
        """Return True if paper trading mode is active."""
        return self._mode == "paper"

    def validate_bet_allowed(self) -> bool:
        """Check if a new bet is allowed in current mode.

        Always returns True for now — this gate is for future
        circuit breakers and risk checks.
        """
        return True

    def get_mode_for_bet(self) -> str:
        """Return the mode string to tag on a new bet record."""
        return self._mode
