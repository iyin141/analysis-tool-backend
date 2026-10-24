import re
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_forecast_service
from app.core.config import settings
from app.core.exceptions import InvalidParameterError
from app.schemas.forecast import DecisionViewResponse
from app.services.forecast_selection import ForecastSelectionService

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/decision-view", response_model=DecisionViewResponse)
async def get_decision_view(
    delivery_date: str = Query(..., alias="deliveryDate", description="Delivery date (YYYY-MM-DD)"),
    cutoff_time: str = Query(settings.default_cutoff_local_time, alias="cutoffTime", description="Decision cutoff local time (HH:MM)"),
    service: ForecastSelectionService = Depends(get_forecast_service),
) -> DecisionViewResponse:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", delivery_date):
        raise InvalidParameterError(
            f"Invalid deliveryDate format: '{delivery_date}'. Expected YYYY-MM-DD.",
            details={"param": "deliveryDate", "value": delivery_date},
        )
    if not re.match(r"^\d{2}:\d{2}$", cutoff_time):
        raise InvalidParameterError(
            f"Invalid cutoffTime format: '{cutoff_time}'. Expected HH:MM.",
            details={"param": "cutoffTime", "value": cutoff_time},
        )

    return service.get_decision_view(delivery_date=delivery_date, cutoff_time_local=cutoff_time)
