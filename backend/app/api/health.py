"""Health check API endpoints.

This module provides health check endpoints for monitoring system status
including database connectivity.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.get_db import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check the health status of all system components.

    Verifies database connectivity status.

    Returns 200 if systems are healthy, else 503 if any are degraded.

    Args:
        db: Database session from dependency injection.

    Returns:
        JSONResponse: Status object with overall health and individual checks.
            - status: "healthy" or "degraded"
            - checks: Dictionary with status of database
    """
    overall = "healthy"
    checks = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks['database'] = 'ok'
    except Exception:
        checks['database'] = 'error'
        overall = "degraded"

    status_code = 200 if overall == 'healthy' else 503

    return JSONResponse(
        status_code=status_code,
        content={
            'status': overall,
            "checks": checks
        }
    )
