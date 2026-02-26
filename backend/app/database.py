"""Database configuration and session management for async SQLAlchemy.

This module provides database engine setup, session factory, and FastAPI
dependency injection for database sessions with automatic commit/rollback.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Database engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    future=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models.

    All database models should inherit from this class to be included
    in Alembic migrations and database operations.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session for FastAPI dependency injection.

    Creates a new database session for each request with automatic
    commit on success and rollback on error.

    Yields:
        AsyncSession: Database session for the request.

    Raises:
        Exception: Re-raises any exception after rolling back the transaction.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Auto commit if no exception
        except Exception:
            await session.rollback()  # Auto-rollback on any error
            raise
