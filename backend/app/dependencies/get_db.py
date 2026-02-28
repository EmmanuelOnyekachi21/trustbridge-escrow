"""Database session dependency for FastAPI.

This module provides database session management for dependency injection
with automatic transaction handling.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


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
