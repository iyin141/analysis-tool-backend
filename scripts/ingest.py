import asyncio
import logging
import sys
from pathlib import Path
import pandas as pd

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.elexon_client import ElexonClient
from app.services.data_repository import DataRepository
from app.core.logging import setup_logging

logger = logging.getLogger("ingest")


async def run_ingestion():
    setup_logging()
    logger.info("Starting ingestion of Elexon data for January 2026 GB Wind...")
    
    client = ElexonClient()
    repo = DataRepository()

    # 1. Fetch Actuals: FUELHH with fuelType == WIND
    # Period: 2026-01-01T00:00:00Z to 2026-02-01T02:00:00Z
    logger.info("Fetching FUELHH stream for actuals (2026-01-01 to 2026-02-01)...")
    fuelhh_items = await client.fetch_fuelhh_stream(
        publish_from="2026-01-01T00:00:00Z",
        publish_to="2026-02-01T02:00:00Z",
    )
    logger.info("Retrieved %d wind actual records from FUELHH", len(fuelhh_items))
    df_act = pd.DataFrame([i.model_dump() for i in fuelhh_items])

    # 2. Fetch Forecasts: WINDFOR stream
    # Needed from late December 2025 (e.g. 2025-12-25) to cover day-ahead cutoffs for Jan 1st through Jan 31st
    logger.info("Fetching WINDFOR stream for forecasts (2025-12-25 to 2026-02-02)...")
    # Chunking into 7-day windows to ensure robust ingestion
    windows = [
        ("2025-12-25T00:00:00Z", "2026-01-01T00:00:00Z"),
        ("2026-01-01T00:00:00Z", "2026-01-08T00:00:00Z"),
        ("2026-01-08T00:00:00Z", "2026-01-15T00:00:00Z"),
        ("2026-01-15T00:00:00Z", "2026-01-22T00:00:00Z"),
        ("2026-01-22T00:00:00Z", "2026-01-29T00:00:00Z"),
        ("2026-01-29T00:00:00Z", "2026-02-02T00:00:00Z"),
    ]

    windfor_all = []
    for w_from, w_to in windows:
        logger.info("Fetching WINDFOR window %s -> %s...", w_from, w_to)
        items = await client.fetch_windfor_stream(w_from, w_to)
        logger.info("Window %s -> %s returned %d items", w_from, w_to, len(items))
        windfor_all.extend(items)

    logger.info("Total WINDFOR items retrieved: %d", len(windfor_all))
    df_for = pd.DataFrame([i.model_dump() for i in windfor_all])

    # 3. Save to Parquet
    repo.save_data(df_act, df_for)
    logger.info("Ingestion completed successfully! Parquet files written to %s", repo.data_dir)


if __name__ == "__main__":
    asyncio.run(run_ingestion())
