from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GB Wind Forecast Decision Support API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Timezone & Decision Defaults
    timezone: str = "Europe/London"
    default_cutoff_local_time: str = "09:00"
    
    # Elexon Insights API
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 30.0
    elexon_max_retries: int = 3
    
    # Data paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    fuelhh_file: Path = Path(__file__).resolve().parent.parent / "data" / "fuelhh_wind_jan2026.parquet"
    windfor_file: Path = Path(__file__).resolve().parent.parent / "data" / "windfor_jan2026.parquet"
    
    # Delivery Scope
    delivery_from: str = "2026-01-01"
    delivery_to: str = "2026-01-31"
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=[
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent.parent / ".env",
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
