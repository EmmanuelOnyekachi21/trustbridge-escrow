"""Flutterwave service dependency injection.

This module provides FastAPI dependencies for accessing the
Flutterwave payment service.
"""

from app.config import settings
from app.services.flutter_wave import FlutterWaveService


def get_flutterwave_service() -> FlutterWaveService:
    """Create and return a Flutterwave service instance.

    Returns:
        Configured FlutterWaveService instance with API credentials.

    Example:
        @router.post("/pay")
        async def pay(
            flutterwave: FlutterWaveService = Depends(get_flutterwave_service)
        ):
            payment_link = await flutterwave.initiate_payment(...)
            return {"link": payment_link}
    """
    flutterwave = FlutterWaveService(
        settings.flutterwave_base_url,
        settings.flutterwave_secret_key
    )
    return flutterwave

