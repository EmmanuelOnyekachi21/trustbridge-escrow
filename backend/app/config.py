"""Application configuration management.

This module defines application settings using Pydantic for environment
variable validation and type safety. Configuration is loaded from .env file.
"""

from enum import Enum
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment enumeration.

    Defines valid deployment environments for the application.
    """

    dev = "dev"
    stag = "staging"
    prod = "prod"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Application name displayed in API documentation.
        environment: Current deployment environment (dev/staging/prod).
        debug: Enable debug mode for development.
        database_url: PostgreSQL connection string.
        sentry_dsn: Sentry DSN for error tracking (optional).
        log_level: Logging level for application logs.
    """

    # APP
    app_name: str = "TrustBridge"
    environment: Environment = Environment.dev
    debug: bool = False

    # Database
    database_url: str

    # Sentry
    sentry_dsn: str = ""

    # logging
    log_level: Literal['DEBUG', "INFO", "ERROR", "WARNING", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
