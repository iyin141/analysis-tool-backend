from typing import List, Optional
from app.schemas.common import CamelModel, DateRange


class OvershootMetric(CamelModel):
    threshold_mw: float
    probability: float


class AccuracyMetrics(CamelModel):
    bias_mw: float
    mae_mw: float
    rmse_mw: float
    nmae_pct: float
    mape_pct: float
    error_p10_mw: float
    error_p50_mw: float
    error_p90_mw: float
    overshoot: OvershootMetric


class DayAccuracyItem(CamelModel):
    date: str
    n: int
    bias_mw: float
    mae_mw: float
    rmse_mw: float


class AccuracySummaryResponse(CamelModel):
    date_range: DateRange
    cutoff_time: str
    sample_size: int
    mean_actual_mw: float
    metrics: AccuracyMetrics
    by_day: List[DayAccuracyItem]


class HourAccuracyBucket(CamelModel):
    hour_of_day: int
    n: int
    bias_mw: float
    mae_mw: float
    rmse_mw: float


class AccuracyByHourResponse(CamelModel):
    buckets: List[HourAccuracyBucket]


class HistogramBin(CamelModel):
    bin_start_mw: float
    bin_end_mw: float
    count: int


class DistributionStats(CamelModel):
    mean_mw: float
    std_mw: float
    skew: float


class DistributionResponse(CamelModel):
    bin_width_mw: float
    bins: List[HistogramBin]
    stats: DistributionStats


class WindLevelBucket(CamelModel):
    label: str
    lower_mw: float
    upper_mw: float
    n: int
    bias_mw: float
    mae_mw: float
    rmse_mw: float


class AccuracyByWindLevelResponse(CamelModel):
    buckets: List[WindLevelBucket]
