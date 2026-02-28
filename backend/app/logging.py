"""Structured logging configuration using structlog.

This module configures structured logging with correlation ID support,
JSON output for production, and colored console output for development.
"""

import logging
import sys
from typing import Any, Dict

import structlog

from app.config import settings


def _add_logger_name(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Attach logger name to every log entry.

    Args:
        logger: Logger instance.
        method_name: Name of the logging method called.
        event_dict: Dictionary containing log event data.

    Returns:
        Modified event dictionary with logger name added.
    """
    event_dict['logger'] = logger.name
    return event_dict


def _add_correlation_id(
    logger: Any,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add correlation ID from context to log entries.

    Args:
        logger: Logger instance.
        method_name: Name of the logging method called.
        event_dict: Dictionary containing log event data.

    Returns:
        Modified event dictionary with correlation ID if available.
    """
    from app.middleware.logging import get_correlation_id

    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging() -> None:
    """Configure structlog and stdlib logging.

    Sets up structured logging with appropriate processors for the
    environment. Uses JSON output for production and colored console
    output for development. Must be called once at application startup.
    """
    # ----------- Standard logging (root) ---------
    logging.basicConfig(
        level=settings.log_level,
        format="%(message)s",
        stream=sys.stdout
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Future proofing
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _add_correlation_id,
        _add_logger_name,
    ]

    if settings.environment == "dev":
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Create or retrieve a structured logger.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured structlog BoundLogger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    return structlog.getLogger(name)
