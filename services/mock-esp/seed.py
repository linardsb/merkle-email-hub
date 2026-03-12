"""Seed all ESP tables from JSON files."""

from pathlib import Path

from database import DatabaseManager

SEED_DIR = Path(__file__).parent / "seed"

SEED_MAP = {
    "braze_content_blocks": "braze.json",
    "sfmc_assets": "sfmc.json",
    "adobe_deliveries": "adobe.json",
    "taxi_templates": "taxi.json",
}


async def seed_all(db: DatabaseManager) -> None:
    """Load all seed JSON files into their respective tables."""
    for table, filename in SEED_MAP.items():
        data_path = str(SEED_DIR / filename)
        await db.seed_from_json(table, data_path)
