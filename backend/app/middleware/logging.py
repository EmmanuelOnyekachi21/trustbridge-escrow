"""Request tracing middleware for correlation ID tracking.

This module provides middleware for tracking requests across the application
using correlation IDs. Correlation IDs can be provided by clients or
automatically generated.
"""

import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging import get_logger

# Context variable to store correlation ID across async calls
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default=None)

logger = get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to each request.

    Features:
        - Accepts X-Correlation-ID header from client or generates new UUID
        - Stores in contextvar for access throughout request lifecycle
        - Adds to response headers for client tracking
        - Logs request start and completion with correlation ID
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID tracking.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler in the chain.

        Returns:
            HTTP response with correlation ID header added.
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            'X-Correlation-ID'
        ) or str(uuid.uuid4())

        # Store in context variable
        correlation_id_var.set(correlation_id)

        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id
        )

        # Process request
        response = await call_next(request)

        # Add correlation id to response headers
        response.headers['X-Correlation-ID'] = correlation_id

        logger.info(
            "Request completed",
            status_code=response.status_code,
            correlation_id=correlation_id
        )

        return response


def get_correlation_id() -> str | None:
    """Get the current request's correlation ID.

    Returns:
        Correlation ID string if within request context, None otherwise.
    """
    return correlation_id_var.get()
