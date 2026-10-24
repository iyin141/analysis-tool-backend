import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import logging

from app.core.config import settings
from app.models.domain import Col

logger = logging.getLogger("wind_forecast.repository")


class DataRepository:
    """
    In-memory and Parquet-backed data repository.
    Enforces standardized pandas schemas for actuals and wind forecasts.
    """
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.data_dir
        self.fuelhh_file = self.data_dir / "fuelhh_wind_jan2026.parquet"
        self.windfor_file = self.data_dir / "windfor_jan2026.parquet"
        
        self.actuals_df = self._standardize_actuals(pd.DataFrame())
        self.forecasts_df = self._standardize_forecasts(pd.DataFrame())
        self.last_updated: Optional[str] = None
        self.load_data()

    def load_data(self) -> None:
        """Loads parquet data from disk into memory if available."""
        if self.fuelhh_file.exists():
            logger.info("Loading actuals from %s", self.fuelhh_file)
            df_act = pd.read_parquet(self.fuelhh_file)
            self.actuals_df = self._standardize_actuals(df_act)
            logger.info("Loaded %d actuals rows", len(self.actuals_df))
        else:
            logger.warning("Parquet file %s not found", self.fuelhh_file)

        if self.windfor_file.exists():
            logger.info("Loading forecasts from %s", self.windfor_file)
            df_for = pd.read_parquet(self.windfor_file)
            self.forecasts_df = self._standardize_forecasts(df_for)
            logger.info("Loaded %d forecasts rows", len(self.forecasts_df))
        else:
            logger.warning("Parquet file %s not found", self.windfor_file)

        if not self.actuals_df.empty:
            mtime = os.path.getmtime(self.fuelhh_file) if self.fuelhh_file.exists() else None
            if mtime:
                import datetime
                self.last_updated = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def save_data(self, actuals_df: pd.DataFrame, forecasts_df: pd.DataFrame) -> None:
        """Saves standardized dataframes to parquet files."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        std_act = self._standardize_actuals(actuals_df)
        std_for = self._standardize_forecasts(forecasts_df)
        
        std_act.to_parquet(self.fuelhh_file, index=False)
        std_for.to_parquet(self.windfor_file, index=False)
        
        self.actuals_df = std_act
        self.forecasts_df = std_for
        
        import datetime
        self.last_updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Saved %d actuals and %d forecasts to %s", len(std_act), len(std_for), self.data_dir)

    def _standardize_actuals(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[
                Col.START_TIME, Col.PUBLISH_TIME, Col.SETTLEMENT_DATE,
                Col.SETTLEMENT_PERIOD, Col.ACTUAL_MW, Col.DELIVERY_DATE
            ])
            
        df = df.copy()
        if "generation" in df.columns and Col.ACTUAL_MW not in df.columns:
            df[Col.ACTUAL_MW] = pd.to_numeric(df["generation"], errors="coerce")
        elif "generation" in df.columns:
            df[Col.ACTUAL_MW] = pd.to_numeric(df["generation"], errors="coerce")
            
        if "startTime" in df.columns:
            df[Col.START_TIME] = df["startTime"]
        if "publishTime" in df.columns:
            df[Col.PUBLISH_TIME] = df["publishTime"]
        if "settlementDate" in df.columns:
            df[Col.SETTLEMENT_DATE] = df["settlementDate"]
        if "settlementPeriod" in df.columns:
            df[Col.SETTLEMENT_PERIOD] = df["settlementPeriod"].astype(int)

        # Derive delivery_date from start_time UTC if not present
        if Col.DELIVERY_DATE not in df.columns:
            df[Col.DELIVERY_DATE] = df[Col.START_TIME].str.slice(0, 10)

        # Drop duplicates by start_time keeping latest publish_time
        df = df.sort_values(Col.PUBLISH_TIME).groupby(Col.START_TIME).last().reset_index()
        return df[[Col.START_TIME, Col.PUBLISH_TIME, Col.SETTLEMENT_DATE, Col.SETTLEMENT_PERIOD, Col.ACTUAL_MW, Col.DELIVERY_DATE]]

    def _standardize_forecasts(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[
                Col.START_TIME, Col.PUBLISH_TIME, Col.FORECAST_MW, Col.HORIZON_HOURS, Col.DELIVERY_DATE
            ])
            
        df = df.copy()
        if "generation" in df.columns and Col.FORECAST_MW not in df.columns:
            df[Col.FORECAST_MW] = pd.to_numeric(df["generation"], errors="coerce")
        elif "generation" in df.columns:
            df[Col.FORECAST_MW] = pd.to_numeric(df["generation"], errors="coerce")

        if "startTime" in df.columns:
            df[Col.START_TIME] = df["startTime"]
        if "publishTime" in df.columns:
            df[Col.PUBLISH_TIME] = df["publishTime"]

        # Horizon hours = (start_time - publish_time)
        start_dt = pd.to_datetime(df[Col.START_TIME], utc=True)
        pub_dt = pd.to_datetime(df[Col.PUBLISH_TIME], utc=True)
        df[Col.HORIZON_HOURS] = (start_dt - pub_dt).dt.total_seconds() / 3600.0

        if Col.DELIVERY_DATE not in df.columns:
            df[Col.DELIVERY_DATE] = df[Col.START_TIME].str.slice(0, 10)

        # Drop duplicates on (start_time, publish_time)
        df = df.drop_duplicates(subset=[Col.START_TIME, Col.PUBLISH_TIME])
        return df[[Col.START_TIME, Col.PUBLISH_TIME, Col.FORECAST_MW, Col.HORIZON_HOURS, Col.DELIVERY_DATE]]

    def get_available_delivery_days(self) -> List[Dict[str, Any]]:
        """Returns list of delivery days with presence of forecasts and actuals."""
        if self.actuals_df.empty and self.forecasts_df.empty:
            return []
            
        act_dates = set(self.actuals_df[Col.DELIVERY_DATE].dropna().unique()) if not self.actuals_df.empty else set()
        for_dates = set(self.forecasts_df[Col.DELIVERY_DATE].dropna().unique()) if not self.forecasts_df.empty else set()
        
        all_dates = sorted(list(act_dates.union(for_dates)))
        # Filter to target month 2026-01
        days = []
        for d in all_dates:
            if d.startswith("2026-01"):
                days.append({
                    "delivery_date": d,
                    "has_forecast": d in for_dates,
                    "has_actuals": d in act_dates,
                })
        return days


data_repo = DataRepository()
