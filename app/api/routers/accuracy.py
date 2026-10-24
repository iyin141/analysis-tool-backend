import re
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_metrics_service
from app.core.config import settings
from app.core.exceptions import InvalidParameterError
from app.schemas.accuracy import (
    AccuracySummaryResponse,
    AccuracyByHourResponse,
    DistributionResponse,
    AccuracyByWindLevelResponse,
)
from app.services.metrics import MetricsService

router = APIRouter(prefix="/accuracy", tags=["Accuracy"])


def _validate_date_range(from_date: str, to_date: str, cutoff_time: str) -> None:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", from_date):
        raise InvalidParameterError(f"Invalid 'from' date format: '{from_date}'. Expected YYYY-MM-DD.")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", to_date):
        raise InvalidParameterError(f"Invalid 'to' date format: '{to_date}'. Expected YYYY-MM-DD.")
    if from_date > to_date:
        raise InvalidParameterError(f"'from' date ({from_date}) cannot be after 'to' date ({to_date}).")
    if not re.match(r"^\d{2}:\d{2}$", cutoff_time):
        raise InvalidParameterError(f"Invalid cutoffTime format: '{cutoff_time}'. Expected HH:MM.")


@router.get("/summary", response_model=AccuracySummaryResponse)
async def get_accuracy_summary(
    from_date: str = Query(settings.delivery_from, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(settings.delivery_to, alias="to", description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query(settings.default_cutoff_local_time, alias="cutoffTime", description="Decision cutoff local time (HH:MM)"),
    overshoot_threshold_mw: float = Query(1000.0, alias="overshootThresholdMw", description="Threshold in MW for under-procurement risk"),
    service: MetricsService = Depends(get_metrics_service),
) -> AccuracySummaryResponse:
    _validate_date_range(from_date, to_date, cutoff_time)
    return service.get_accuracy_summary(
        from_date=from_date,
        to_date=to_date,
        cutoff_time_local=cutoff_time,
        overshoot_threshold_mw=overshoot_threshold_mw,
    )


@router.get("/by-hour", response_model=AccuracyByHourResponse)
async def get_accuracy_by_hour(
    from_date: str = Query(settings.delivery_from, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(settings.delivery_to, alias="to", description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query(settings.default_cutoff_local_time, alias="cutoffTime", description="Decision cutoff local time (HH:MM)"),
    service: MetricsService = Depends(get_metrics_service),
) -> AccuracyByHourResponse:
    _validate_date_range(from_date, to_date, cutoff_time)
    return service.get_accuracy_by_hour(
        from_date=from_date,
        to_date=to_date,
        cutoff_time_local=cutoff_time,
    )


@router.get("/distribution", response_model=DistributionResponse)
async def get_accuracy_distribution(
    from_date: str = Query(settings.delivery_from, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(settings.delivery_to, alias="to", description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query(settings.default_cutoff_local_time, alias="cutoffTime", description="Decision cutoff local time (HH:MM)"),
    bin_width_mw: float = Query(250.0, alias="binWidthMw", description="Histogram bin width in MW"),
    service: MetricsService = Depends(get_metrics_service),
) -> DistributionResponse:
    _validate_date_range(from_date, to_date, cutoff_time)
    if bin_width_mw <= 0:
        raise InvalidParameterError("binWidthMw must be strictly greater than 0.")
    return service.get_distribution(
        from_date=from_date,
        to_date=to_date,
        cutoff_time_local=cutoff_time,
        bin_width_mw=bin_width_mw,
    )


@router.get("/by-wind-level", response_model=AccuracyByWindLevelResponse)
async def get_accuracy_by_wind_level(
    from_date: str = Query(settings.delivery_from, alias="from", description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(settings.delivery_to, alias="to", description="End date (YYYY-MM-DD)"),
    cutoff_time: str = Query(settings.default_cutoff_local_time, alias="cutoffTime", description="Decision cutoff local time (HH:MM)"),
    service: MetricsService = Depends(get_metrics_service),
) -> AccuracyByWindLevelResponse:
    _validate_date_range(from_date, to_date, cutoff_time)
    return service.get_accuracy_by_wind_level(
        from_date=from_date,
        to_date=to_date,
        cutoff_time_local=cutoff_time,
    )
