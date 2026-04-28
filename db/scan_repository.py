"""Repository for scan_settings persistence."""
import logging
from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


class ScanRepository:
    """CRUD for the single-row scan_settings table."""

    def get_enabled(self) -> bool:
        """Return current scan enabled state. Defaults to True if row missing."""
        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT enabled FROM scan_settings WHERE id = 1")
                row = cur.fetchone()
                if row is None:
                    # Seed the row if missing
                    cur.execute("INSERT INTO scan_settings (id, enabled) VALUES (1, true)")
                    return True
                return row[0]
        except Exception:
            logger.exception("Error reading scan_settings, defaulting to enabled")
            return True

    def set_enabled(self, enabled: bool) -> bool:
        """Update scan enabled state."""
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE scan_settings SET enabled = %s WHERE id = 1",
                    (enabled,),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO scan_settings (id, enabled) VALUES (1, %s)",
                        (enabled,),
                    )
            logger.info(f"Scan setting updated: enabled={enabled}")
            return True
        except Exception:
            logger.exception("Error updating scan_settings")
            return False
