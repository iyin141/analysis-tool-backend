from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from app.models.domain import Col, HalfHourSlot
from app.utils.time import compute_d_minus_1_cutoff, get_delivery_day_slots, to_utc_iso


def select_forecasts_as_of_cutoff(
    forecasts_df: pd.DataFrame,
    delivery_date: str,
    cutoff_time_local: str = "09:00",
) -> pd.DataFrame:
    """
    Selects the latest forecast published at or before the D-1 decision cutoff for each target half-hour slot.
    Guarantees:
    - No look-ahead leakage (publish_time <= decision cutoff on D-1).
    - Preserves all 48 (or 46/50 on clock change) half-hour slots for delivery day D.
    - Missing forecast periods explicitly represented as NaN (not dropped).
    """
    slots = get_delivery_day_slots(delivery_date)
    slots_df = pd.DataFrame([
        {
            Col.START_TIME: s.start_time,
            Col.SETTLEMENT_DATE: s.settlement_date,
            Col.SETTLEMENT_PERIOD: s.settlement_period,
            Col.HOUR_OF_DAY: s.hour_of_day,
            Col.DELIVERY_DATE: delivery_date,
        }
        for s in slots
    ])

    if forecasts_df.empty:
        slots_df[Col.FORECAST_MW] = np.nan
        slots_df[Col.PUBLISH_TIME] = None
        slots_df[Col.HORIZON_HOURS] = np.nan
        return slots_df

    cutoff_utc = compute_d_minus_1_cutoff(delivery_date, cutoff_time_local)
    cutoff_utc_iso = to_utc_iso(cutoff_utc)

    # Filter forecasts strictly published at or before cutoff
    valid_f = forecasts_df[forecasts_df[Col.PUBLISH_TIME] <= cutoff_utc_iso].copy()

    if valid_f.empty:
        slots_df[Col.FORECAST_MW] = np.nan
        slots_df[Col.PUBLISH_TIME] = None
        slots_df[Col.HORIZON_HOURS] = np.nan
        return slots_df

    # For each start_time, take the latest publish_time available before cutoff
    latest_f = (
        valid_f.sort_values(Col.PUBLISH_TIME)
        .groupby(Col.START_TIME)
        .last()
        .reset_index()
    )

    merged = pd.merge(
        slots_df,
        latest_f[[Col.START_TIME, Col.PUBLISH_TIME, Col.FORECAST_MW, Col.HORIZON_HOURS]],
        on=Col.START_TIME,
        how="left",
    )

    return merged
