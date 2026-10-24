from dataclasses import dataclass
from typing import Optional


class Col:
    """Canonical DataFrame column names across data layers."""
    DATASET = "dataset"
    PUBLISH_TIME = "publish_time"
    START_TIME = "start_time"
    SETTLEMENT_DATE = "settlement_date"
    SETTLEMENT_PERIOD = "settlement_period"
    FUEL_TYPE = "fuel_type"
    GENERATION = "generation"
    
    # Processed / merged columns
    FORECAST_MW = "forecast_mw"
    ACTUAL_MW = "actual_mw"
    ERROR_MW = "error_mw"
    HORIZON_HOURS = "horizon_hours"
    DELIVERY_DATE = "delivery_date"
    HOUR_OF_DAY = "hour_of_day"


@dataclass(frozen=True)
class HalfHourSlot:
    start_time: str
    settlement_date: str
    settlement_period: int
    hour_of_day: int


@dataclass(frozen=True)
class CutoffWindow:
    delivery_date: str
    cutoff_time_local: str
    cutoff_utc_iso: str
    start_utc_iso: str
    end_utc_iso: str
