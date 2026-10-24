import re
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_horizon_service
from app.core.config import settings
from app.core.exceptions import InvalidParameterError
from app.schemas.horizon import HorizonAnalysisResponse
from app.services.horizon import HorizonService

router = APIRouter(prefix="/horizon", tags=["Horizon"])


@router.get("/analysis", response_model=HorizonAnalysisResponse)
async def get_horizon_analysis(
    from_date: str = Query(settings.delivery_from, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(settings.delivery_to, alias="to", description="End date (YYYY-MM-DD)"),
    horizon_bin_hours: float = Query(3.0, alias="horizonBinHours", description="Horizon bin width in hours"),
    service: HorizonService = Depends(get_horizon_service),
) -> HorizonAnalysisResponse:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", from_date):
        raise InvalidParameterError(f"Invalid 'from' date format: '{from_date}'. Expected YYYY-MM-DD.")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", to_date):
        raise InvalidParameterError(f"Invalid 'to' date format: '{to_date}'. Expected YYYY-MM-DD.")
    if from_date > to_date:
        raise InvalidParameterError(f"'from' date ({from_date}) cannot be after 'to' date ({to_date}).")
    if horizon_bin_hours <= 0:
        raise InvalidParameterError("horizonBinHours must be strictly positive.")

    return service.get_horizon_analysis(
        from_date=from_date,
        to_date=to_date,
        horizon_bin_hours=horizon_bin_hours,
    )
