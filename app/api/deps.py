from app.services.data_repository import data_repo, DataRepository
from app.services.forecast_selection import ForecastSelectionService
from app.services.metrics import MetricsService
from app.services.horizon import HorizonService
from app.clients.elexon_client import ElexonClient


def get_data_repository() -> DataRepository:
    return data_repo


def get_forecast_service() -> ForecastSelectionService:
    return ForecastSelectionService(data_repo)


def get_metrics_service() -> MetricsService:
    return MetricsService(data_repo)


def get_horizon_service() -> HorizonService:
    return HorizonService(data_repo)


def get_elexon_client() -> ElexonClient:
    return ElexonClient()
