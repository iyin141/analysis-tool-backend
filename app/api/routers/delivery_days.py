from fastapi import APIRouter, Depends
from typing import List

from app.api.deps import get_data_repository
from app.core.config import settings
from app.schemas.delivery_days import DeliveryDaysResponse, DeliveryDayItem
from app.services.data_repository import DataRepository
from app.utils.time import compute_d_minus_1_cutoff, to_utc_iso

router = APIRouter(tags=["Delivery Days"])


@router.get("/delivery-days", response_model=DeliveryDaysResponse)
async def get_delivery_days(
    repo: DataRepository = Depends(get_data_repository)
) -> DeliveryDaysResponse:
    raw_days = repo.get_available_delivery_days()
    
    # If no data ingested yet, synthesize the target delivery days from settings
    if not raw_days:
        from datetime import datetime, timedelta
        start_d = datetime.strptime(settings.delivery_from, "%Y-%m-%d")
        end_d = datetime.strptime(settings.delivery_to, "%Y-%m-%d")
        curr = start_d
        raw_days = []
        while curr <= end_d:
            raw_days.append({
                "delivery_date": curr.strftime("%Y-%m-%d"),
                "has_forecast": False,
                "has_actuals": False,
            })
            curr += timedelta(days=1)

    days_dto: List[DeliveryDayItem] = []
    for d in raw_days:
        cutoff_dt = compute_d_minus_1_cutoff(d["delivery_date"], settings.default_cutoff_local_time)
        days_dto.append(
            DeliveryDayItem(
                delivery_date=d["delivery_date"],
                decision_cutoff=to_utc_iso(cutoff_dt),
                has_forecast=d.get("has_forecast", False),
                has_actuals=d.get("has_actuals", False),
            )
        )

    return DeliveryDaysResponse(
        timezone=settings.timezone,
        default_cutoff_local_time=settings.default_cutoff_local_time,
        days=days_dto,
    )
