from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import pandas as pd
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from pydantic import ConfigDict

from app.api.deps import get_data_repository, get_elexon_client
from app.clients.elexon_client import ElexonClient
from app.services.data_repository import DataRepository
from app.schemas.common import CamelModel
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


class RefreshResponse(CamelModel):
    status: str
    actuals_rows: int
    forecast_rows: int
    refreshed_at: str


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_data(
    repo: DataRepository = Depends(get_data_repository),
    client: ElexonClient = Depends(get_elexon_client),
) -> RefreshResponse:
    # Pull fresh data based on configured delivery scope
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(settings.delivery_from, "%Y-%m-%d")
    end_dt = datetime.strptime(settings.delivery_to, "%Y-%m-%d") + timedelta(days=1)
    windfor_start_dt = start_dt - timedelta(days=7)

    fuelhh_items = await client.fetch_fuelhh_stream(
        start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        end_dt.strftime("%Y-%m-%dT00:00:00Z")
    )
    windfor_items = await client.fetch_windfor_stream(
        windfor_start_dt.strftime("%Y-%m-%dT00:00:00Z"),
        end_dt.strftime("%Y-%m-%dT00:00:00Z")
    )

    df_act = pd.DataFrame([item.model_dump() for item in fuelhh_items])
    df_for = pd.DataFrame([item.model_dump() for item in windfor_items])

    repo.save_data(df_act, df_for)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return RefreshResponse(
        status="ok",
        actuals_rows=len(repo.actuals_df),
        forecast_rows=len(repo.forecasts_df),
        refreshed_at=now_iso,
    )
