"""Dependency injection for currency service.

This module provides FastAPI dependencies for accessing the
currency exchange rate service.
"""

from typing import Annotated

from fastapi import Depends

from app.services.currency import CurrencyRateService


async def get_currency_service() -> CurrencyRateService:
    """Return the singleton currency service instance.

    This instance is created once at startup in the lifespan context
    and reused for all requests.

    The service is stored as a global variable in main.py and accessed
    via import at call time to avoid circular import issues.

    Returns:
        Configured CurrencyRateService singleton instance.

    Raises:
        RuntimeError: If service hasn't been initialized (app not started).

    Example:
        @router.get("/convert")
        async def convert_currency(
            currency_service: CurrencyServiceDep
        ):
            rate = await currency_service.get_rate("NGN")
            return {"rate": rate}
    """
    # Import here to avoid circular import
    from app.main import _currency_service

    if _currency_service is None:
        raise RuntimeError(
            "Currency service not initialized. "
            "This should not happen if the app started correctly."
        )

    return _currency_service


# Type alias for cleaner endpoint signatures
# Usage: async def my_endpoint(currency_service: CurrencyServiceDep):
CurrencyServiceDep = Annotated[
    CurrencyRateService,
    Depends(get_currency_service)
]