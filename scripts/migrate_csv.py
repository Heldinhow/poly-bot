#!/usr/bin/env python3
"""One-time migration script: CSV paper_trades.csv -> PostgreSQL bets table.

Idempotent — running twice will not duplicate records.
"""

import csv
import logging
import sys
from pathlib import Path

from db.connection import init_schema, health_check
from db.repository import BetRepository
from models.bet import Bet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_csv(csv_path: str = "paper_trades.csv") -> dict:
    """Migrate CSV data to PostgreSQL."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.warning(f"CSV file not found: {csv_file}")
        return {"total": 0, "migrated": 0, "skipped": 0}

    # Ensure schema exists
    init_schema()

    repo = BetRepository()
    total = 0
    migrated = 0
    skipped = 0

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            try:
                bet = Bet.from_csv_row(row)

                # Check for existing record (same market_id + timestamp)
                existing = repo.get_bet_by_market_id(bet.market_id)
                if existing and existing.timestamp == bet.timestamp:
                    logger.debug(f"Skipping duplicate: {bet.market_id}")
                    skipped += 1
                    continue

                repo.create_bet(bet)
                migrated += 1
                logger.info(f"Migrated: {bet.market_id} | {bet.question[:50]}")

            except Exception as e:
                logger.error(f"Failed to migrate row {total}: {e}")
                skipped += 1

    return {"total": total, "migrated": migrated, "skipped": skipped}


def main() -> int:
    logger.info("=" * 50)
    logger.info("CSV -> PostgreSQL Migration")
    logger.info("=" * 50)

    # Health check
    if not health_check():
        logger.error("Database is not reachable. Is PostgreSQL running?")
        return 1

    result = migrate_csv()

    logger.info("=" * 50)
    logger.info("Migration complete")
    logger.info(f"  Total rows in CSV:  {result['total']}")
    logger.info(f"  Migrated to DB:     {result['migrated']}")
    logger.info(f"  Skipped/duplicates: {result['skipped']}")
    logger.info("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
