from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from app.models.domain import Col
from app.services.cutoff import select_forecasts_as_of_cutoff
from app.services.data_repository import DataRepository
from app.schemas.forecast import (
    DecisionViewResponse,
    ForecastPoint,
    ForecastSummary,
    UncertaintyBandMeta,
)
from app.utils.time import compute_d_minus_1_cutoff, to_utc_iso


class ForecastSelectionService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def get_decision_view(
        self,
        delivery_date: str,
        cutoff_time_local: str = "09:00",
    ) -> DecisionViewResponse:
        cutoff_utc = compute_d_minus_1_cutoff(delivery_date, cutoff_time_local)
        cutoff_utc_iso = to_utc_iso(cutoff_utc)

        # 1. As-of-cutoff forecasts for delivery day D
        forecasts_day = select_forecasts_as_of_cutoff(
            self.repo.forecasts_df,
            delivery_date=delivery_date,
            cutoff_time_local=cutoff_time_local,
        )

        # 2. Actuals for delivery day D
        actuals_day = self.repo.actuals_df[
            self.repo.actuals_df[Col.DELIVERY_DATE] == delivery_date
        ].copy()

        # Merge slots with actuals
        if not actuals_day.empty:
            merged = pd.merge(
                forecasts_day,
                actuals_day[[Col.START_TIME, Col.ACTUAL_MW]],
                on=Col.START_TIME,
                how="left",
            )
        else:
            merged = forecasts_day.copy()
            merged[Col.ACTUAL_MW] = np.nan

        # Compute error = forecast - actual where both are present
        merged[Col.ERROR_MW] = merged[Col.FORECAST_MW] - merged[Col.ACTUAL_MW]

        # 3. Compute uncertainty band based on history strictly BEFORE day D
        band_low_offset, band_high_offset, based_on_days, is_in_sample = self._compute_historical_error_band(
            delivery_date=delivery_date,
            cutoff_time_local=cutoff_time_local,
        )

        # Compute band per point: forecast - upper_error_offset, forecast - lower_error_offset
        # Because error = forecast - actual => actual = forecast - error
        # Thus 80% confidence interval for actuals: [forecast - P90(error), forecast - P10(error)]
        # When actual is bounded by [0, inf), clamp low to 0.
        points: List[ForecastPoint] = []
        for _, row in merged.iterrows():
            f_mw = float(row[Col.FORECAST_MW]) if pd.notna(row[Col.FORECAST_MW]) else None
            a_mw = float(row[Col.ACTUAL_MW]) if pd.notna(row[Col.ACTUAL_MW]) else None
            err_mw = float(row[Col.ERROR_MW]) if pd.notna(row[Col.ERROR_MW]) else None
            horiz = float(row[Col.HORIZON_HOURS]) if pd.notna(row[Col.HORIZON_HOURS]) else None
            pub_time = str(row[Col.PUBLISH_TIME]) if pd.notna(row[Col.PUBLISH_TIME]) else None

            if f_mw is not None and band_low_offset is not None and band_high_offset is not None:
                # band low and high around forecast
                b_low = max(0.0, f_mw - band_high_offset)
                b_high = max(0.0, f_mw - band_low_offset)
            else:
                b_low = None
                b_high = None

            points.append(
                ForecastPoint(
                    start_time=row[Col.START_TIME],
                    settlement_period=int(row[Col.SETTLEMENT_PERIOD]),
                    forecast_mw=round(f_mw, 1) if f_mw is not None else None,
                    forecast_publish_time=pub_time,
                    horizon_hours=round(horiz, 1) if horiz is not None else None,
                    actual_mw=round(a_mw, 1) if a_mw is not None else None,
                    error_mw=round(err_mw, 1) if err_mw is not None else None,
                    band_low_mw=round(b_low, 1) if b_low is not None else None,
                    band_high_mw=round(b_high, 1) if b_high is not None else None,
                )
            )

        # 4. Summary metrics
        valid_forecasts = merged[Col.FORECAST_MW].dropna()
        valid_actuals = merged[Col.ACTUAL_MW].dropna()

        avg_f = float(valid_forecasts.mean()) if not valid_forecasts.empty else None
        peak_f = float(valid_forecasts.max()) if not valid_forecasts.empty else None
        min_f = float(valid_forecasts.min()) if not valid_forecasts.empty else None
        total_f_mwh = float(valid_forecasts.sum() * 0.5) if not valid_forecasts.empty else None
        total_a_mwh = float(valid_actuals.sum() * 0.5) if not valid_actuals.empty else None

        missing_f = int(merged[Col.FORECAST_MW].isna().sum())
        missing_a = int(merged[Col.ACTUAL_MW].isna().sum())

        valid_pubs = merged[Col.PUBLISH_TIME].dropna()
        latest_pub = str(valid_pubs.max()) if not valid_pubs.empty else None

        summary = ForecastSummary(
            avg_forecast_mw=round(avg_f, 1) if avg_f is not None else None,
            peak_forecast_mw=round(peak_f, 1) if peak_f is not None else None,
            min_forecast_mw=round(min_f, 1) if min_f is not None else None,
            forecast_total_mwh=round(total_f_mwh, 1) if total_f_mwh is not None else None,
            actual_total_mwh=round(total_a_mwh, 1) if total_a_mwh is not None else None,
            missing_forecast_periods=missing_f,
            missing_actual_periods=missing_a,
            latest_publish_time_used=latest_pub,
        )

        band_meta = UncertaintyBandMeta(
            lower_percentile=10,
            upper_percentile=90,
            based_on_days=based_on_days,
            band_is_in_sample=is_in_sample,
        )

        return DecisionViewResponse(
            delivery_date=delivery_date,
            decision_cutoff=cutoff_utc_iso,
            points=points,
            summary=summary,
            band=band_meta,
        )

    def _compute_historical_error_band(
        self,
        delivery_date: str,
        cutoff_time_local: str,
    ) -> Tuple[Optional[float], Optional[float], int, bool]:
        """
        Computes P10 and P90 error offsets strictly using historical days < delivery_date.
        If history is < 3 days, falls back to all-period errors with band_is_in_sample = True.
        """
        all_dates = sorted([
            d for d in self.repo.actuals_df[Col.DELIVERY_DATE].dropna().unique()
            if d.startswith("2026-01")
        ])

        prior_dates = [d for d in all_dates if d < delivery_date]

        errors_list: List[float] = []
        is_in_sample = False
        target_dates = prior_dates

        if len(prior_dates) < 3:
            # Fall back to all available days in sample
            target_dates = all_dates
            is_in_sample = True

        for d in target_dates:
            f_df = select_forecasts_as_of_cutoff(self.repo.forecasts_df, d, cutoff_time_local)
            a_df = self.repo.actuals_df[self.repo.actuals_df[Col.DELIVERY_DATE] == d]
            if not f_df.empty and not a_df.empty:
                m = pd.merge(f_df, a_df[[Col.START_TIME, Col.ACTUAL_MW]], on=Col.START_TIME)
                errs = (m[Col.FORECAST_MW] - m[Col.ACTUAL_MW]).dropna().tolist()
                errors_list.extend(errs)

        if not errors_list:
            return None, None, 0, is_in_sample

        arr = np.array(errors_list)
        p10 = float(np.percentile(arr, 10))
        p90 = float(np.percentile(arr, 90))

        return p10, p90, len(target_dates), is_in_sample
