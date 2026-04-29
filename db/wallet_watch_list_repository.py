import logging
from dataclasses import dataclass
from typing import Optional

from db.connection import get_db_cursor

logger = logging.getLogger(__name__)


@dataclass
class WatchedWallet:
    id: str
    wallet_address: str
    label: str
    weight: float
    active: bool
    created_at: str


@dataclass
class WalletPosition:
    condition_id: str
    title: str
    outcome: str
    size: float
    avg_price: float
    current_value: float
    cash_pnl: float


class WalletWatchListRepository:
    """Repository for managing wallets to copy trades from."""

    def get_all(self):
        """Return all watched wallets."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM wallet_watch_list ORDER BY created_at DESC")
            return cursor.fetchall()

    def get_active(self):
        """Return active wallets to copy from."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM wallet_watch_list WHERE active = TRUE ORDER BY created_at DESC"
            )
            return cursor.fetchall()

    def _normalize_address(self, address: str) -> str:
        """Strip numeric proxy-wallet suffix (e.g. 0x...-123456 -> 0x...)."""
        import re
        # If address ends with -<number>, strip it to get the clean wallet
        cleaned = re.sub(r'-\d+$', '', address.strip())
        return cleaned

    def add(self, wallet_address: str, label: str, weight: float = 1.0) -> str:
        """Add a wallet to the watch list. Returns its id."""
        clean_address = self._normalize_address(wallet_address)
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO wallet_watch_list (wallet_address, label, weight)
                VALUES (%s, %s, %s)
                ON CONFLICT (wallet_address) DO UPDATE SET
                    label = EXCLUDED.label,
                    weight = EXCLUDED.weight,
                    active = TRUE
                RETURNING id
                """,
                (clean_address, label, weight)
            )
            row = cursor.fetchone()
            logger.info(f"Wallet added to watch list: {wallet_address} ({label})")
            return row["id"]

    def remove(self, wallet_id: str) -> bool:
        """Remove (deactivate) a wallet from the watch list."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE wallet_watch_list SET active = FALSE WHERE id = %s",
                (wallet_id,)
            )
            return cursor.rowcount > 0

    def set_active(self, wallet_id: str, active: bool) -> None:
        """Enable or disable a watched wallet."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE wallet_watch_list SET active = %s WHERE id = %s",
                (active, wallet_id)
            )
