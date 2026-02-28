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

from app.api import auth


configure_logging()

_initialize_firebase()

logger = get_logger(__name__)


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
    logger.info("TrustBridge started!")

    yield

    await engine.dispose()

    logger.info("TrustBridge out")


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

