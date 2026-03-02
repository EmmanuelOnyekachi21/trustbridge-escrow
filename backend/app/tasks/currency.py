# app/tasks/currency
"""Background tasks for currency exchange rate management.

This module contains Celery tasks that run periodically to keep
exchange rates fresh in Redis cache.
"""

from app.logging import get_logger
from decimal import Decimal
from app.celery_app import celery_app
from app.services.currency import CurrencyRateService
from app.config import settings

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.refresh_exchange_rates",
    bind=True,  # Pass task instance as first argument
    max_retries=3,  # Retry up to 3 times on failure.
    default_retry_delay=300,  # Wait 5 minutes between retries.
)
def refresh_exchange_rates(self):
    """Fetch latest exchange rates and update Redis cache.
    
    This task runs every 30 minutes (configured in celery_app.py beat_schedule).
    
    Flow:
    1. Fetch rates from external API
    2. Cache rates in Redis with 30-minute TTL
    3. Log success/failure
    4. Retry on failure (up to 3 times)
    
    Why this is a Celery task:
    - Runs in background (doesn't block API requests)
    - Scheduled automatically (no manual intervention)
    - Retries on failure (resilient to temporary API issues)
    - Monitored (can track success/failure in Celery logs)
    
    Returns:
        dict: Status information about the refresh operation
    """

    logger.info("Starting exchange rates refresh task")

    try:
        # Initialize currency service
        currency_service = CurrencyRateService(
            api_key=settings.exchange_rates_api_key,
            redis_url=settings.redis_url
        )

        # Fresh rates from API
        logger.info("Fetching fresh exchange rates from API")
        rates = await_sync(currency_service._fetch_rates_from_api())

        logger.info(f"Fetched {len(rates)} exchange rates: {list(rates.keys())}")

        # Cache the rates
        logger.info("Caching exchange rates in Redis")
        await_sync(currency_service.cache_rates(rates))

        # log success with rate details
        rate_summary = {
            currency: float(rate)
            for currency, rate in rates.items()
        }
        logger.info(f"Successfully refreshed exchange rates: {rate_summary}")

        return {
            'status': 'success',
            'rates_updated': len(rates),
            'currencies': list(rates.keys()),
            'rates': rate_summary
        }
    except Exception as exc:
        # log error with full context
        logger.error(
            f"Failed to refresh exchange rates: {exc}",
            exc_info=True # Include stack trace
        )

        # Retry the task because API might be temporarily down
        # Why countdown? Don't hammer API immediately

        try:
            raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes
        except self.MaxRetriesExceededError:
            # All retries exhausted
            logger.critical(
                "Exchange rate refresh failed after all retries. "
                "Manual intervention may be required."
            )

            # Send alert (email, Slack, PagerDuty)
            return {
                "status": "failed",
                "error": str(exc),
                "retry_attempts_exhausted": True
            }

def await_sync(coroutine):
    """Helper to run async code in sync Celery task.
    
    Why needed? Celery tasks are synchronous by default,
    but our CurrencyRateService uses async/await.
    
    Args:
        coroutine: Async function to run
    
    Returns:
        Result of the coroutine
    
    Implementation notes:
    - Always creates a new event loop for safety
    - Closes loop after use to prevent resource leaks
    - Works reliably in Celery worker threads
    """
    import asyncio

    # Always create a fresh event loop
    # Why? Celery workers might have closed loops from previous tasks
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the coroutine
        return loop.run_until_complete(coroutine)
    finally:
        # Clean up: close the loop to free resources
        loop.close()

# Optional: Manual refresh task (for testing or emergency use)
@celery_app.task(name="app.tasks.currency.refresh_exchange_rates_now")
def refresh_exchange_rates_now():
    """Manually trigger exchange rate refresh.
    
    Usage:
        # From Python code
        from app.tasks.currency import refresh_exchange_rates_now
        refresh_exchange_rates_now.delay()
        
        # From command line
        celery -A app.celery_app call app.tasks.currency.refresh_exchange_rates_now
    """
    return refresh_exchange_rates()
