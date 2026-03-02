"""Currency exchange rate API endpoints.

This module provides endpoints for testing the currency service
and checking exchange rates.
"""

from decimal import Decimal
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies.currency import CurrencyServiceDep

router = APIRouter(prefix="/currency", tags=["currency"])


class ExchangeRateResponse(BaseModel):
    """Response model for a single exchange rate.

    Attributes:
        currency: Currency code (e.g., NGN, GHS).
        rate: Exchange rate as Decimal.
    """

    currency: str
    rate: Decimal

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "currency": "NGN",
                "rate": "1495.5"
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model for currency service health check.

    Attributes:
        status: Health status string.
        redis_connected: Whether Redis is connected.
        supported_currencies: List of supported currency codes.
    """

    status: str
    redis_connected: bool
    supported_currencies: List[str]

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "redis_connected": True,
                "supported_currencies": ["USD", "NGN", "GHS", "KES"]
            }
        }


@router.get("/health", response_model=HealthCheckResponse)
async def currency_service_health(
    currency_service: CurrencyServiceDep
):
    """Check if currency service is healthy and Redis is connected.

    This endpoint verifies:
        - Currency service singleton is initialized
        - Redis connection is active
        - Supported currencies are available

    Args:
        currency_service: Currency service from dependency injection.

    Returns:
        HealthCheckResponse with status and connection information.
    """
    redis_connected = currency_service._redis_client is not None

    return HealthCheckResponse(
        status="healthy",
        redis_connected=redis_connected,
        supported_currencies=list(currency_service.SUPPORTED_CURRENCIES)
    )


@router.get("/rates/{currency}", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    currency: str,
    currency_service: CurrencyServiceDep
):
    """Get exchange rate for a specific currency.

    Args:
        currency: Currency code (e.g., NGN, GHS, KES).
        currency_service: Currency service from dependency injection.

    Returns:
        ExchangeRateResponse with currency and rate.

    Raises:
        HTTPException: 400 if currency is invalid, 500 if fetch fails.

    Example:
        GET /currency/rates/NGN
        Response: {"currency": "NGN", "rate": "1495.5"}
    """
    try:
        rate = await currency_service.get_rate(currency.upper())
        return ExchangeRateResponse(
            currency=currency.upper(),
            rate=rate
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch exchange rate"
        )


@router.get("/test-singleton")
async def test_singleton(currency_service: CurrencyServiceDep):
    """Test endpoint to verify singleton pattern is working.

    This endpoint returns the memory address of the service instance.
    If you call it multiple times, the address should be the same,
    proving that the same instance is being reused.

    Args:
        currency_service: Currency service from dependency injection.

    Returns:
        Dictionary with instance IDs and helpful message.

    Example:
        GET /currency/test-singleton
        Response: {
            "instance_id": "140234567890123",
            "redis_client_id": "140234567890456",
            "message": "Same IDs across requests = singleton working!"
        }
    """
    redis_client_id = (
        str(id(currency_service._redis_client))
        if currency_service._redis_client
        else "None"
    )

    return {
        "instance_id": str(id(currency_service)),
        "redis_client_id": redis_client_id,
        "message": "Same IDs across requests = singleton working!",
        "tip": "Call this endpoint multiple times and compare instance_id"
    }
