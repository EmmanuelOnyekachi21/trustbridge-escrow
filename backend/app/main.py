"""TrustBridge FastAPI application entry point.

This module initializes the FastAPI application with middleware, logging,
error tracking, and API routers. It manages application lifecycle including
database connection cleanup.
"""

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from app.api import health
from app.config import settings
from app.database import engine
from app.logging import configure_logging, get_logger
from app.middleware.logging import RequestTracingMiddleware

from app.core.firebase import _initialize_firebase

from app.api import auth, currency

from app.services.currency import CurrencyRateService


configure_logging()

_initialize_firebase()

logger = get_logger(__name__)


_currency_service: CurrencyRateService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events.

    Handles startup and shutdown operations including database connection
    cleanup.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control to the application during its runtime.
    """
    global _currency_service

    logger.info("TrustBridge started!")

    # Startup: Create currency service singleton
    logger.info("Starting up: Creating currency service...")
    _currency_service = CurrencyRateService(
        api_key=settings.exchange_rates_api_key,
        redis_url=settings.redis_url
    )

    # Pre-connect to Redis (optional but good practice)
    await _currency_service._get_redis_client()
    logger.info("Currency service ready with Redis connection")

    yield

    # Shutdown: Cleanup resources
    logger.info("Shutting down: Closing Redis connection...")
    if _currency_service and _currency_service._redis_client:
        await _currency_service._redis_client.close()
    logger.info("Redis connection closed")

    await engine.dispose()

    logger.info("TrustBridge shutdown complete")


# Initializing sentry dsn
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)

# Add request tracing middleware
app.add_middleware(RequestTracingMiddleware)

app.include_router(health.router)
app.include_router(auth.router, prefix='/auth')
app.include_router(currency.router)

