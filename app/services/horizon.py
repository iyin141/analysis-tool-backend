from typing import Dict, Any, List
import pandas as pd
import numpy as np

from app.models.domain import Col
from app.services.data_repository import DataRepository
from app.utils.stats import compute_metrics
from app.schemas.horizon import HorizonAnalysisResponse, HorizonBucket


class HorizonService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def get_horizon_analysis(
        self,
        from_date: str,
        to_date: str,
        horizon_bin_hours: float = 3.0,
        max_horizon_hours: float = 72.0,
    ) -> HorizonAnalysisResponse:
        """
        Evaluates forecast error across ALL forecast vintages (not just as-of-cutoff)
        binned by forecast horizon (startTime - publishTime).
        Demonstrates the quantitative value of waiting closer to real time.
        """
        if self.repo.forecasts_df.empty or self.repo.actuals_df.empty:
            return HorizonAnalysisResponse(horizon_bin_hours=horizon_bin_hours, buckets=[])

        # Filter actuals within [from_date, to_date]
        act_filtered = self.repo.actuals_df[
            (self.repo.actuals_df[Col.DELIVERY_DATE] >= from_date) &
            (self.repo.actuals_df[Col.DELIVERY_DATE] <= to_date)
        ]

        if act_filtered.empty:
            return HorizonAnalysisResponse(horizon_bin_hours=horizon_bin_hours, buckets=[])

        # Merge all forecast vintages with actuals on start_time
        merged = pd.merge(
            self.repo.forecasts_df[[Col.START_TIME, Col.FORECAST_MW, Col.HORIZON_HOURS]],
            act_filtered[[Col.START_TIME, Col.ACTUAL_MW]],
            on=Col.START_TIME,
            how="inner",
        )

        merged = merged.dropna(subset=[Col.FORECAST_MW, Col.ACTUAL_MW, Col.HORIZON_HOURS])
        # Horizon must be positive (forecast published strictly before or at start_time)
        merged = merged[(merged[Col.HORIZON_HOURS] >= 0) & (merged[Col.HORIZON_HOURS] <= max_horizon_hours)]

        if merged.empty:
            return HorizonAnalysisResponse(horizon_bin_hours=horizon_bin_hours, buckets=[])

        # Bin by horizon_bin_hours
        num_bins = int(np.ceil(max_horizon_hours / horizon_bin_hours))
        buckets: List[HorizonBucket] = []

        for b in range(num_bins):
            h_min = b * horizon_bin_hours
            h_max = (b + 1) * horizon_bin_hours
            
            group = merged[
                (merged[Col.HORIZON_HOURS] >= h_min) &
                (merged[Col.HORIZON_HOURS] < h_max)
            ]

            if not group.empty:
                g_f = group[Col.FORECAST_MW].to_numpy()
                g_a = group[Col.ACTUAL_MW].to_numpy()
                m = compute_metrics(g_f, g_a)
                buckets.append(
                    HorizonBucket(
                        horizon_min_hours=h_min,
                        horizon_max_hours=h_max,
                        n=len(group),
                        bias_mw=m["bias_mw"],
                        mae_mw=m["mae_mw"],
                        rmse_mw=m["rmse_mw"],
                    )
                )

        return HorizonAnalysisResponse(
            horizon_bin_hours=horizon_bin_hours,
            buckets=buckets,
        )
