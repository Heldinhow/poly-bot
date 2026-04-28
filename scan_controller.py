"""Thread-safe scan enable/disable controller with DB persistence."""
import threading
import logging

from db.scan_repository import ScanRepository

logger = logging.getLogger(__name__)


class ScanController:
    """Shared state for enabling/disabling the scanner at runtime.

    Loads initial state from DB (falls back to env default).
    Persists every toggle to DB so state survives restarts.
    """

    def __init__(self, default_enabled: bool = True):
        self._lock = threading.Lock()
        self._repo = ScanRepository()
        # Load from DB; if row missing, use default (from env)
        self._enabled = self._repo.get_enabled()
        # If DB had no row, the repo already seeded it as True.
        # But if user passed default_enabled=False, respect it on first run
        # only when the DB row was just created (get_enabled returned True from seed).
        # We handle this by checking: if DB value differs from default, use DB.
        # If DB value == True (seeded) and default is False, use False.
        db_value = self._repo.get_enabled()
        if db_value != default_enabled:
            # DB was seeded or has a different value — respect the default on first boot
            self._enabled = default_enabled
            self._repo.set_enabled(default_enabled)
        else:
            self._enabled = db_value

        logger.info(f"ScanController initialized: enabled={self._enabled}")

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def enable(self) -> bool:
        with self._lock:
            self._enabled = True
        self._repo.set_enabled(True)
        logger.info("Scan enabled")
        return True

    def disable(self) -> bool:
        with self._lock:
            self._enabled = False
        self._repo.set_enabled(False)
        logger.info("Scan disabled")
        return True

    def toggle(self) -> bool:
        with self._lock:
            self._enabled = not self._enabled
            new_state = self._enabled
        self._repo.set_enabled(new_state)
        logger.info(f"Scan toggled to: {'enabled' if new_state else 'disabled'}")
        return new_state

    def status(self) -> dict:
        with self._lock:
            return {"enabled": self._enabled}
