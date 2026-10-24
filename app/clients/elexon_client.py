import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import UpstreamError
from app.schemas.elexon import FuelHHEntry, WindforEntry

logger = logging.getLogger("wind_forecast.elexon_client")


class ElexonClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = base_url or settings.elexon_base_url
        self.timeout = timeout or settings.elexon_timeout_seconds
        self.max_retries = settings.elexon_max_retries

    async def fetch_fuelhh_stream(
        self,
        publish_from: str,
        publish_to: str,
    ) -> List[FuelHHEntry]:
        """Fetches FUELHH stream and validates records matching fuelType == 'WIND'."""
        url = f"{self.base_url}/datasets/FUELHH/stream"
        params = {
            "publishDateTimeFrom": publish_from,
            "publishDateTimeTo": publish_to,
        }
        
        raw_items = await self._get_with_retry(url, params)
        validated: List[FuelHHEntry] = []
        for item in raw_items:
            if item.get("fuelType") == "WIND":
                try:
                    validated.append(FuelHHEntry.model_validate(item))
                except Exception as e:
                    logger.debug("Skipping invalid FUELHH row: %s", e)
        return validated

    async def fetch_windfor_stream(
        self,
        publish_from: str,
        publish_to: str,
    ) -> List[WindforEntry]:
        """Fetches WINDFOR stream and validates records."""
        url = f"{self.base_url}/datasets/WINDFOR/stream"
        params = {
            "publishDateTimeFrom": publish_from,
            "publishDateTimeTo": publish_to,
        }
        
        raw_items = await self._get_with_retry(url, params)
        validated: List[WindforEntry] = []
        for item in raw_items:
            try:
                validated.append(WindforEntry.model_validate(item))
            except Exception as e:
                logger.debug("Skipping invalid WINDFOR row: %s", e)
        return validated

    async def _get_with_retry(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": "GB-Wind-Forecast-Decision-Support/1.0"}
        
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code == 200:
                        return resp.json()
                    logger.warning(
                        "Upstream Elexon error attempt %d/%d: status=%d %s",
                        attempt, self.max_retries, resp.status_code, resp.text[:200]
                    )
            except Exception as e:
                logger.warning(
                    "Network error fetching from Elexon attempt %d/%d: %s",
                    attempt, self.max_retries, str(e)
                )
                
            if attempt < self.max_retries:
                await asyncio.sleep(1.5 * attempt)

        raise UpstreamError(
            f"Failed to fetch data from Elexon API after {self.max_retries} attempts."
        )
