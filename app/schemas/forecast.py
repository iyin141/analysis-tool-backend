from typing import List, Optional
from app.schemas.common import CamelModel


class ForecastPoint(CamelModel):
    start_time: str
    settlement_period: int
    forecast_mw: Optional[float] = None
    forecast_publish_time: Optional[str] = None
    horizon_hours: Optional[float] = None
    actual_mw: Optional[float] = None
    error_mw: Optional[float] = None
    band_low_mw: Optional[float] = None
    band_high_mw: Optional[float] = None


class ForecastSummary(CamelModel):
    avg_forecast_mw: Optional[float] = None
    peak_forecast_mw: Optional[float] = None
    min_forecast_mw: Optional[float] = None
    forecast_total_mwh: Optional[float] = None
    actual_total_mwh: Optional[float] = None
    missing_forecast_periods: int = 0
    missing_actual_periods: int = 0
    latest_publish_time_used: Optional[str] = None


class UncertaintyBandMeta(CamelModel):
    lower_percentile: int = 10
    upper_percentile: int = 90
    based_on_days: int = 0
    band_is_in_sample: bool = False


class DecisionViewResponse(CamelModel):
    delivery_date: str
    decision_cutoff: str
    points: List[ForecastPoint]
    summary: ForecastSummary
    band: UncertaintyBandMeta
