"""Health check endpoint tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from backend.app.main import app
from backend.app.dependencies.get_db import get_db


@pytest.mark.asyncio
async def test_health_check_success():
    """Test health check returns 200 when database is healthy."""
    # Mock database to return success
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["checks"]["database"] == "ok"
    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_database_error():
    """Test health check returns 503 when database fails."""
    # Mock database to raise exception
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
    app.dependency_overrides[get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"
        assert response.json()["checks"]["database"] == "error"
    
    app.dependency_overrides.clear()
