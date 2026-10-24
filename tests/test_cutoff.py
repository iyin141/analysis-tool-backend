import pytest
import pandas as pd
import numpy as np

from app.models.domain import Col
from app.services.cutoff import select_forecasts_as_of_cutoff


def test_as_of_cutoff_selection_no_lookahead():
    # Setup mock forecasts for delivery day 2026-01-15
    # Target slot: 2026-01-15T00:00:00Z
    # Cutoff is D-1 (2026-01-14) at 09:00:00Z
    forecast_data = [
        # Published on D-2: should be superseded by D-1 06:00
        {Col.START_TIME: "2026-01-15T00:00:00Z", Col.PUBLISH_TIME: "2026-01-13T12:00:00Z", Col.FORECAST_MW: 4000.0, Col.HORIZON_HOURS: 36.0, Col.DELIVERY_DATE: "2026-01-15"},
        # Published on D-1 at 06:00: before cutoff, should be selected!
        {Col.START_TIME: "2026-01-15T00:00:00Z", Col.PUBLISH_TIME: "2026-01-14T06:00:00Z", Col.FORECAST_MW: 5000.0, Col.HORIZON_HOURS: 18.0, Col.DELIVERY_DATE: "2026-01-15"},
        # Published on D-1 at 14:00: AFTER CUTOFF! Must NOT be selected (lookahead leakage)
        {Col.START_TIME: "2026-01-15T00:00:00Z", Col.PUBLISH_TIME: "2026-01-14T14:00:00Z", Col.FORECAST_MW: 7000.0, Col.HORIZON_HOURS: 10.0, Col.DELIVERY_DATE: "2026-01-15"},
    ]
    df_for = pd.DataFrame(forecast_data)
    
    result = select_forecasts_as_of_cutoff(df_for, delivery_date="2026-01-15", cutoff_time_local="09:00")
    
    # 48 periods generated for 2026-01-15
    assert len(result) == 48
    row_0 = result[result[Col.START_TIME] == "2026-01-15T00:00:00Z"].iloc[0]
    
    # Exactly 5000.0 from 06:00 (the latest before cutoff 09:00)
    assert row_0[Col.FORECAST_MW] == 5000.0
    assert row_0[Col.PUBLISH_TIME] == "2026-01-14T06:00:00Z"


def test_as_of_cutoff_missing_forecast_preserves_slot():
    # Only forecast for period 1, none for other 47 periods
    forecast_data = [
        {Col.START_TIME: "2026-01-15T00:00:00Z", Col.PUBLISH_TIME: "2026-01-14T08:00:00Z", Col.FORECAST_MW: 5500.0, Col.HORIZON_HOURS: 16.0, Col.DELIVERY_DATE: "2026-01-15"},
    ]
    df_for = pd.DataFrame(forecast_data)
    
    result = select_forecasts_as_of_cutoff(df_for, delivery_date="2026-01-15", cutoff_time_local="09:00")
    
    assert len(result) == 48
    # Period 1 present
    assert result.iloc[0][Col.FORECAST_MW] == 5500.0
    # Period 2 missing, NaN not dropped
    assert pd.isna(result.iloc[1][Col.FORECAST_MW])
