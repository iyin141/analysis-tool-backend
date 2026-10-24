from fastapi import APIRouter, Depends
from app.api.deps import get_data_repository
from app.core.config import settings
from app.schemas.common import HealthResponse
from app.services.data_repository import DataRepository

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(repo: DataRepository = Depends(get_data_repository)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        data_last_updated=repo.last_updated,
    )
