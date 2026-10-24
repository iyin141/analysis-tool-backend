from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from app.models.domain import Col
from app.services.cutoff import select_forecasts_as_of_cutoff
from app.services.data_repository import DataRepository
from app.utils.stats import compute_metrics, compute_distribution
from app.schemas.accuracy import (
    AccuracySummaryResponse,
    AccuracyMetrics,
    DayAccuracyItem,
    AccuracyByHourResponse,
    HourAccuracyBucket,
    DistributionResponse,
    HistogramBin,
    DistributionStats,
    AccuracyByWindLevelResponse,
    WindLevelBucket,
    OvershootMetric,
)
from app.schemas.common import DateRange


class MetricsService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def _get_merged_as_of_cutoff_range(
        self,
        from_date: str,
        to_date: str,
        cutoff_time_local: str = "09:00",
    ) -> pd.DataFrame:
        """
        Gathers as-of-cutoff forecasts and actuals across all dates within [from_date, to_date].
        """
        all_dates = sorted([
            d for d in self.repo.actuals_df[Col.DELIVERY_DATE].dropna().unique()
            if from_date <= d <= to_date
        ])

        frames: List[pd.DataFrame] = []
        for d in all_dates:
            f_df = select_forecasts_as_of_cutoff(self.repo.forecasts_df, d, cutoff_time_local)
            a_df = self.repo.actuals_df[self.repo.actuals_df[Col.DELIVERY_DATE] == d]
            if not f_df.empty and not a_df.empty:
                m = pd.merge(
                    f_df,
                    a_df[[Col.START_TIME, Col.ACTUAL_MW]],
                    on=Col.START_TIME,
                    how="inner",
                )
                frames.append(m)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.dropna(subset=[Col.FORECAST_MW, Col.ACTUAL_MW])
        combined[Col.ERROR_MW] = combined[Col.FORECAST_MW] - combined[Col.ACTUAL_MW]
        return combined

    def get_accuracy_summary(
        self,
        from_date: str,
        to_date: str,
        cutoff_time_local: str = "09:00",
        overshoot_threshold_mw: float = 1000.0,
    ) -> AccuracySummaryResponse:
        df = self._get_merged_as_of_cutoff_range(from_date, to_date, cutoff_time_local)
        
        if df.empty:
            metrics_dict = compute_metrics(np.array([]), np.array([]), overshoot_threshold_mw)
            return AccuracySummaryResponse(
                date_range=DateRange(from_date=from_date, to_date=to_date),
                cutoff_time=cutoff_time_local,
                sample_size=0,
                mean_actual_mw=0.0,
                metrics=AccuracyMetrics(
                    bias_mw=metrics_dict["bias_mw"],
                    mae_mw=metrics_dict["mae_mw"],
                    rmse_mw=metrics_dict["rmse_mw"],
                    nmae_pct=metrics_dict["nmae_pct"],
                    mape_pct=metrics_dict["mape_pct"],
                    error_p10_mw=metrics_dict["error_p10_mw"],
                    error_p50_mw=metrics_dict["error_p50_mw"],
                    error_p90_mw=metrics_dict["error_p90_mw"],
                    overshoot=OvershootMetric(
                        threshold_mw=overshoot_threshold_mw,
                        probability=metrics_dict["overshoot"]["probability"],
                    ),
                ),
                by_day=[],
            )

        f_vals = df[Col.FORECAST_MW].to_numpy()
        a_vals = df[Col.ACTUAL_MW].to_numpy()
        mean_act = float(np.mean(a_vals))
        metrics_dict = compute_metrics(f_vals, a_vals, overshoot_threshold_mw)

        # By day breakdown
        by_day: List[DayAccuracyItem] = []
        for d, group in df.groupby(Col.DELIVERY_DATE):
            g_f = group[Col.FORECAST_MW].to_numpy()
            g_a = group[Col.ACTUAL_MW].to_numpy()
            g_metrics = compute_metrics(g_f, g_a, overshoot_threshold_mw)
            by_day.append(
                DayAccuracyItem(
                    date=str(d),
                    n=len(group),
                    bias_mw=g_metrics["bias_mw"],
                    mae_mw=g_metrics["mae_mw"],
                    rmse_mw=g_metrics["rmse_mw"],
                )
            )

        return AccuracySummaryResponse(
            date_range=DateRange(from_date=from_date, to_date=to_date),
            cutoff_time=cutoff_time_local,
            sample_size=len(df),
            mean_actual_mw=round(mean_act, 1),
            metrics=AccuracyMetrics(
                bias_mw=metrics_dict["bias_mw"],
                mae_mw=metrics_dict["mae_mw"],
                rmse_mw=metrics_dict["rmse_mw"],
                nmae_pct=metrics_dict["nmae_pct"],
                mape_pct=metrics_dict["mape_pct"],
                error_p10_mw=metrics_dict["error_p10_mw"],
                error_p50_mw=metrics_dict["error_p50_mw"],
                error_p90_mw=metrics_dict["error_p90_mw"],
                overshoot=OvershootMetric(
                    threshold_mw=overshoot_threshold_mw,
                    probability=metrics_dict["overshoot"]["probability"],
                ),
            ),
            by_day=by_day,
        )

    def get_accuracy_by_hour(
        self,
        from_date: str,
        to_date: str,
        cutoff_time_local: str = "09:00",
    ) -> AccuracyByHourResponse:
        df = self._get_merged_as_of_cutoff_range(from_date, to_date, cutoff_time_local)
        if df.empty:
            return AccuracyByHourResponse(buckets=[])

        buckets: List[HourAccuracyBucket] = []
        for hour in range(24):
            group = df[df[Col.HOUR_OF_DAY] == hour]
            if not group.empty:
                g_f = group[Col.FORECAST_MW].to_numpy()
                g_a = group[Col.ACTUAL_MW].to_numpy()
                m = compute_metrics(g_f, g_a)
                buckets.append(
                    HourAccuracyBucket(
                        hour_of_day=hour,
                        n=len(group),
                        bias_mw=m["bias_mw"],
                        mae_mw=m["mae_mw"],
                        rmse_mw=m["rmse_mw"],
                    )
                )
            else:
                buckets.append(
                    HourAccuracyBucket(
                        hour_of_day=hour,
                        n=0,
                        bias_mw=0.0,
                        mae_mw=0.0,
                        rmse_mw=0.0,
                    )
                )

        return AccuracyByHourResponse(buckets=buckets)

    def get_distribution(
        self,
        from_date: str,
        to_date: str,
        cutoff_time_local: str = "09:00",
        bin_width_mw: float = 250.0,
    ) -> DistributionResponse:
        df = self._get_merged_as_of_cutoff_range(from_date, to_date, cutoff_time_local)
        if df.empty:
            return DistributionResponse(
                bin_width_mw=bin_width_mw,
                bins=[],
                stats=DistributionStats(mean_mw=0.0, std_mw=0.0, skew=0.0),
            )

        errors = df[Col.ERROR_MW].to_numpy()
        dist_dict = compute_distribution(errors, bin_width_mw)

        bins_dto = [
            HistogramBin(
                bin_start_mw=b["bin_start_mw"],
                bin_end_mw=b["bin_end_mw"],
                count=b["count"],
            )
            for b in dist_dict["bins"]
        ]
        stats_dto = DistributionStats(
            mean_mw=dist_dict["stats"]["mean_mw"],
            std_mw=dist_dict["stats"]["std_mw"],
            skew=dist_dict["stats"]["skew"],
        )

        return DistributionResponse(
            bin_width_mw=bin_width_mw,
            bins=bins_dto,
            stats=stats_dto,
        )

    def get_accuracy_by_wind_level(
        self,
        from_date: str,
        to_date: str,
        cutoff_time_local: str = "09:00",
    ) -> AccuracyByWindLevelResponse:
        df = self._get_merged_as_of_cutoff_range(from_date, to_date, cutoff_time_local)
        if df.empty:
            return AccuracyByWindLevelResponse(buckets=[])

        # Define 5 distinct wind level tiers (in MW)
        tiers = [
            ("0-3 GW (Low)", 0.0, 3000.0),
            ("3-7 GW (Moderate)", 3000.0, 7000.0),
            ("7-11 GW (Medium)", 7000.0, 11000.0),
            ("11-15 GW (High)", 11000.0, 15000.0),
            ("15+ GW (Very High)", 15000.0, 100000.0),
        ]

        buckets: List[WindLevelBucket] = []
        for label, low, high in tiers:
            group = df[(df[Col.ACTUAL_MW] >= low) & (df[Col.ACTUAL_MW] < high)]
            if not group.empty:
                g_f = group[Col.FORECAST_MW].to_numpy()
                g_a = group[Col.ACTUAL_MW].to_numpy()
                m = compute_metrics(g_f, g_a)
                buckets.append(
                    WindLevelBucket(
                        label=label,
                        lower_mw=low,
                        upper_mw=high if high < 50000 else 20000.0,
                        n=len(group),
                        bias_mw=m["bias_mw"],
                        mae_mw=m["mae_mw"],
                        rmse_mw=m["rmse_mw"],
                    )
                )
            else:
                buckets.append(
                    WindLevelBucket(
                        label=label,
                        lower_mw=low,
                        upper_mw=high if high < 50000 else 20000.0,
                        n=0,
                        bias_mw=0.0,
                        mae_mw=0.0,
                        rmse_mw=0.0,
                    )
                )

        return AccuracyByWindLevelResponse(buckets=buckets)
