from app.schemas.forecast import ForecastPoint, UncertaintyBandMeta, DecisionViewResponse, ForecastSummary
from app.schemas.accuracy import OvershootMetric, AccuracyMetrics, AccuracySummaryResponse
from app.schemas.common import DateRange


def test_camel_case_serialization():
    point = ForecastPoint(
        start_time="2026-01-15T00:00:00Z",
        settlement_period=1,
        forecast_mw=4980.5,
        forecast_publish_time="2026-01-14T06:00:00Z",
        horizon_hours=18.0,
        actual_mw=5123.0,
        error_mw=-142.5,
        band_low_mw=4200.0,
        band_high_mw=5600.0,
    )
    
    dumped = point.model_dump(by_alias=True)
    assert "startTime" in dumped
    assert "settlementPeriod" in dumped
    assert "forecastMw" in dumped
    assert "forecastPublishTime" in dumped
    assert "horizonHours" in dumped
    assert "actualMw" in dumped
    assert "errorMw" in dumped
    assert "bandLowMw" in dumped
    assert "bandHighMw" in dumped


def test_band_meta_camel_case():
    meta = UncertaintyBandMeta(
        lower_percentile=10,
        upper_percentile=90,
        based_on_days=14,
        band_is_in_sample=False,
    )
    dumped = meta.model_dump(by_alias=True)
    assert dumped["lowerPercentile"] == 10
    assert dumped["upperPercentile"] == 90
    assert dumped["basedOnDays"] == 14
    assert dumped["bandIsInSample"] is False
