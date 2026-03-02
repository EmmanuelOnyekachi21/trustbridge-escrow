"""Currency exchange rate service.

This module provides a service for fetching and caching exchange rates
with Redis caching and external API integration.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Optional

import httpx
import redis.asyncio as redis

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)


class CurrencyRateService:
    """Service for fetching and caching exchange rates.

    Design decisions:
        - Uses USD as base currency (industry standard)
        - Async operations to avoid blocking FastAPI
        - Filters to only supported currencies (saves memory, faster lookups)
        - Comprehensive error handling with logging

    Attributes:
        SUPPORTED_CURRENCIES: Set of supported currency codes.
        CACHE_TTL_SECONDS: Cache time-to-live in seconds.
        CACHE_KEY_PREFIX: Redis key prefix for exchange rates.
        DISPLAY_DECIMAL_PLACES: Number of decimal places for display.
    """

    # Define supported currencies as a class constant
    SUPPORTED_CURRENCIES = {'USD', 'NGN', 'GHS', 'KES'}

    # Class constant for cache configuration
    CACHE_TTL_SECONDS = 1800
    CACHE_KEY_PREFIX = "exchange_rate"

    # Rounding figure
    DISPLAY_DECIMAL_PLACES = 2

    def __init__(self, api_key: str, redis_url: str):
        """Initialize with API key and Redis connection.

        Args:
            api_key: ExchangeRate-API key.
            redis_url: Redis connection URL.
        """
        self.api_key = api_key
        self.base_url = 'https://v6.exchangerate-api.com/v6/'
        self.redis_url = redis_url
        self._redis_client = None
    
    async def _get_redis_client(self) -> redis.Redis:
        """
        Get or create Redis client connection.

        Lazy initialization = "Don't do work until you absolutely need to.

        Why lazy initialization?
        - Don't connect to Redis until we actually need it
        - Allows service to be created without Redis being available
        - Connection is reused across multiple calls
        """
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connection established")
        
        return self._redis_client
    
    async def cache_rates(self, rates: Dict[str, Decimal]) -> None:
        """
        Store exchange rates in Redis cache with expiration.
        
        Args:
            rates: Dictionary mapping currency codes to rates
                   Example: {"USD": Decimal("1"), "NGN": Decimal("1495.5")}
        
        Raises:
            redis.RedisError: If Redis connection or write fails
        
        Design decisions:
        - Stores each currency as separate key (easier to fetch individual rates)
        - Key pattern: "exchange_rate:NGN" = "1495.5"
        - Sets TTL (time-to-live) so stale rates auto-expire
        - Uses pipeline for atomic batch writes (faster, more reliable)
        """

        if not rates:
            logger.warning("Attempted to cache empty rates dictionary")
            return
        
        try:
            # Step 1: Get Redis connection
            redis_client = await self._get_redis_client()

            # step2: Use pipeline for batch operations
            # Why pipeline?
            # - Without: 4 seperate network round-trips (slow)
            # - With: 1 network round-trip for all 4 writes (fast)
            # - Atomic: all succeed or all fail (consistency)
            async with redis_client.pipeline(transaction=True) as pipe:
                # Add each rate to the pipeline
                for currency, rate in rates.items():
                    key = f"{self.CACHE_KEY_PREFIX}:{currency}"

                    # convert Decimal to string
                    value = str(rate)

                    # Add SET command to the pipeline
                    # We use setex not set because
                    # - setex: SET with EXpiration in one atomic operation
                    # - set + expire: Two operations, not atpomic (race condition)
                    pipe.setex(
                        name=key,
                        time=self.CACHE_TTL_SECONDS,
                        value=value
                    )

                    logger.debug(f"Queued cache write: {key} = {value} (TTL: {self.CACHE_TTL_SECONDS}s)")
                
                # Execute all commands atomically
                # await execute()? Sends all commands to Redis at once
                await pipe.execute()
            
            logger.info(f"Cached {len(rates)} exchange rates to Redis")
        except redis.RedisError as e:
            # Distinguishes Redis issues from other errors
            # Caller can decid: fail hard or continue without cache
            logger.error(f"Failed to cache exchange rates in Redis: {e}")
            raise
    
        except Exception as e:
            logger.error(f"Unexpected error during rate caching: {e}")
            raise
    
    async def get_rate(self, currency: str) -> Decimal:
        """
        Get exchange rate for a currency (USD base).

        Args:
            currency: Currency code (e.g., 'NGN', 'GHS', 'KES')
        
        Returns:
            Exchange rate as Decimal.
        
        Raises:
            ValueError: If currency isn't supported
        
        Flow:
        1. Check if currency is supported.
        2. Try to read from Redis cache (fast path)
        3. If cache miss, fetch from API and cache (slow path)
        4. Return the rate.

        Design decisions:
        - Grateful degradation: If Redis fails, fetch from API directly
        - Cache-aside pattern: Apllication manages cache, not database
        - Automatic cache refresh on miss
        """

        if currency not in self.SUPPORTED_CURRENCIES:
            logger.warning(f"Unsuported currency requested: {currency}")
            raise ValueError(
                f"Currency {currency} not supported. "
                f"Supported: {', '.join(self.SUPPORTED_CURRENCIES)}"
            )
        
        # Try to read from cache (fast path)
        try:
            rate = await self._get_rate_from_cache(currency)

            if rate is not None:
                # Cache hit! Return immediately
                logger.debug(f"cache hit for {currency}: {rate}")
                return rate
            
            # Cache miss - continue to slow path
            logger.info(f"Cache miss for {currency}, fetching from API")
        except redis.RedisError as e:
            # Redis is down or connection failed.
            logger.warning(f"Redis error, falling back to API: {e}")
            # Continue to slow path

        # Slow path: fetch from API
        rates = await self._fetch_rates_from_api()

        # Try to cache the rates
        # I use try...except so if caching fails, we still have the data
        try:
            await self.cache_rates(rates)
        except redis.RedisError as e:
            # Caching failed, but we have the data
            # Log and continue (graceful degradation)
            logger.warning(f"Failed to cache rates: {e}")
        
        # Return the requested rate
        if currency not in rates:
            logger.error(f"Requested currency {currency} not in fetched rates")
            raise ValueError(f"Could not obtain rate for {currency}")
        
        return rates[currency]
    
    async def _get_rate_from_cache(self, currency: str) -> Decimal:
        """
        Retrieve a rate from Redis cache.

        Args:
            currency: Currency code to fetch

        Returns:
            Rate as Decimal if found, None if not found

        Raises:
            redis.RedisError: If Redis connection fails
        """
        # Get redis client
        redis_client = await self._get_redis_client()

        # Build cache key
        key = f"{self.CACHE_KEY_PREFIX}:{currency}"

        # Read from Redis
        cached_value = await redis_client.get(key)

        # Handle cache miss
        if cached_value is None:
            logger.debug(f"Cache miss for {key}")
            return None
        
        # Convert string back to Decimal
        try:
            rate = Decimal(cached_value)
            logger.debug(f"Cache hit for {currency}: {rate}")
            return rate
        except (ValueError, TypeError) as e:
            # Corrupted data in cache (shouldn't happen but defensive)
            logger.warning(f"Corrupted cache data for {key}: {cached_value}. Removing.")
            await redis_client.delete(key)  # Remove corrupted data
            # Treat as cache miss
            return None

    async def _fetch_rates_from_api(self) -> Dict[str, Decimal]:
        """
        Fetch latest exchange rates from external API.

        Returns:
            Dictionary mapping currency codes to rates (as Decimal for precision)
            Example: {"USD": Decimal("1"), "NGN": Decimal("1495.5")}
        
        Raises:
            ValueError: If API key is invalid or quota exceeded
            httpx.HTTPError: If network request fails
            KeyError: If API response format is unexpected
        
        Design decisions:
        - Async to avoid blocking (FastAPI is async)
        - Returns Decimal not float (financial precision matters!)
        - Raises specific exceptions (caller can handle appropriately)
        - Logs all errors (debugging in production)
        """
        url = f"{self.base_url}/{self.api_key}/latest/USD"

        logger.info(f"Fetching exchange rates from {self.base_url}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                response.raise_for_status()  # Raise exception for bad status codes

                # Parse JSON
                data = response.json()
        except httpx.TimeoutException:
            logger.error("Exchange rate API request timed out.")
            raise ValueError("Exchange rate service is slow or unavailable")
        except httpx.HTTPError as e:
            logger.error(f"Exchange rate API request failed: {e}")
            raise ValueError(f"Failed to fetch exchange rates from external service: {e}")
        
        if data.get('result') != 'success':
            error_type = data.get('error-type', 'unknown')
            
            # Why separate error types? Different errors need different handling
            if error_type == 'invalid-key':
                logger.error("Invalid exchange rate API key")
                raise ValueError("Invalid exchange rate API key - check configuration")
            
            elif error_type == 'quota-reached':
                logger.error("Exchange rate API quota exceeded")
                raise ValueError("Exchange rate API quota exceeded - try again later")
            
            elif error_type == 'unsupported-code':
                logger.error("USD base currency not supported by API")
                raise ValueError("Base currency USD not supported")
            
            else:
                logger.error(f"Exchange rate API error: {error_type}")
                raise ValueError(f"Exchange rate API error: {error_type}")
        
        conversion_rates = data.get('conversion_rates', {})
        
        if not conversion_rates:
            logger.error("No conversion rates in API response")
            raise ValueError("Exchange rate API returned empty rates")
        

        filtered_rates = {}

        for currency in self.SUPPORTED_CURRENCIES:
            if currency not in conversion_rates:
                logger.warning(f"Currency {currency} not found in API response")
                continue

            rate_value = conversion_rates[currency]
            filtered_rates[currency] = Decimal(str(rate_value))
        

        # Validate we got critical currencies
        # USD is the base.  It must always be present.

        if 'USD' not in filtered_rates:
            logger.error("USD rate missing from API response")
            raise ValueError("USD rate missing - cannot proceed")
        
        # - Need USD + at least one other to do conversions
        if len(filtered_rates) < 2:
            logger.error(f"Only {len(filtered_rates)} currencies fetched, need at least 2")
            raise ValueError("Insufficient currencies fetched from API")
        
        logger.info(f"Successfully fetched {len(filtered_rates)} exchange rates")
        
        # Step 11: Return the rates
        return filtered_rates
    
    async def convert(self, amount: Decimal, from_currency: str, to_currency: str, round_result: bool = True) -> Decimal:
        """Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert (e.g., Decimal("150000"))
            from_currency: Source currency code (e.g., "NGN")
            to_currency: Target currency code (e.g., "USD")
            round_result: Whether to round to 2 decimal places (default: True)
        
        Returns:
            Converted amount as Decimal
            
        Raises:
            ValueError: If amount is invalid or currencies not supported
        
        Examples:
            # Convert 150,000 NGN to USD
            >>> await convert(Decimal("150000"), "NGN", "USD")
            Decimal("100.30")
            
            # Convert 100 USD to GHS
            >>> await convert(Decimal("100"), "USD", "GHS")
            Decimal("1520.00")
            
            # Convert between non-USD currencies
            >>> await convert(Decimal("1000"), "NGN", "GHS")
            Decimal("10.16")
        
        Design decisions:
        - Uses USD as intermediate currency (industry standard)
        - Full precision during calculation, rounds only at end
        - Validates inputs before fetching rates (fail fast)
        - Same-currency conversion returns original amount (optimization)
        """
        # Validate amount
        if amount <= 0:
            logger.warning(f"Invalid amount for conversion: {amount}")
            raise ValueError(f"Amount must be positive, got {amount}")
        
        # Normalize currency code because user might send 'ngn' instead of 'NGN'
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Validate currencies to avoid unnecessary API/Cache calls.
        # Say user sets from_currency='NGN', and to_currency='NGN'
        if from_currency == to_currency:
            logger.debug(f"Same currency conversion: {from_currency}")
            # Still round if requested (e.g., 100.123 -> 100.12)
            if round_result:
                return amount.quantize(
                    Decimal(f"0.{'0' * self.DISPLAY_DECIMAL_PLACES}"),
                    rounding=ROUND_HALF_UP
                )
            return amount

        # Get exchange rates from redis
        logger.info(f"Converting {amount} {from_currency} to {to_currency}")
        rate_from_currency = await self.get_rate(from_currency)
        rate_to_currency = await self.get_rate(to_currency)

        if rate_from_currency == 0:
            logger.error(f"Zero exchange rate for {from_currency}")
            raise ValueError(f"Invalid exchange rate for {from_currency}")
        
        # Calculate conversion
        conversion_rate = rate_to_currency / rate_from_currency
        result = amount * conversion_rate

        logger.debug(
            f"Conversion: {amount} {from_currency} × "
            f"({rate_to_currency} / {rate_from_currency}) = {result} {to_currency}"
        )

        # Round result if requested
        if round_result:
            # quantize() rounds to specified decimal places
            result = result.quantize(
                Decimal(f"0.{'0' * self.DISPLAY_DECIMAL_PLACES}"),
                rounding=ROUND_HALF_UP
            )
            logger.debug(f"Rounded result: {result} {to_currency}")
        
        return result
    
    async def convert_to_usd(
        self,
        amount: Decimal,
        from_currency: str,
        round_result: bool = True
    ) -> Decimal:
        """Convenience method to convert any currency to USD.
        
        This is the most common conversion in the system.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            round_result: Whether to round result
        
        Returns:
            Amount in USD
        
        Example:
            >>> await convert_to_usd(Decimal("150000"), "NGN")
            Decimal("100.30")
        """
        return await self.convert(amount, from_currency, "USD", round_result)
    
    async def convert_from_usd(
        self,
        amount: Decimal,
        to_currency: str,
        round_result: bool = True
    ) -> Decimal:
        """Convenience method to convert USD to any currency.
        
        Args:
            amount: Amount in USD
            to_currency: Target currency code
            round_result: Whether to round result
        
        Returns:
            Amount in target currency
        
        Example:
            >>> await convert_from_usd(Decimal("100"), "NGN")
            Decimal("149550.00")
        """
        return await self.convert(amount, "USD", to_currency, round_result)




