from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.error_handlers import register_error_handlers
from app.services.data_repository import data_repo

# Routers
from app.api.routers.health import router as health_router
from app.api.routers.delivery_days import router as delivery_days_router
from app.api.routers.forecast import router as forecast_router
from app.api.routers.accuracy import router as accuracy_router
from app.api.routers.horizon import router as horizon_router
from app.api.routers.admin import router as admin_router

logger = logging.getLogger("wind_forecast.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing GB Wind Forecast Decision Support API (v%s)...", settings.app_version)
    data_repo.load_data()
    yield
    logger.info("Shutting down API...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register custom exception handlers
    register_error_handlers(app)

    # Health check at top-level
    app.include_router(health_router)

    # API v1 routes
    v1_prefix = "/api/v1"
    app.include_router(health_router, prefix=v1_prefix)
    app.include_router(delivery_days_router, prefix=v1_prefix)
    app.include_router(forecast_router, prefix=v1_prefix)
    app.include_router(accuracy_router, prefix=v1_prefix)
    app.include_router(horizon_router, prefix=v1_prefix)
    app.include_router(admin_router, prefix=v1_prefix)

    return app


app = create_app()
