"""User authentication dependency for FastAPI.

This module provides dependency injection for authenticating users via
Firebase tokens and managing user records in the database.
"""

import asyncio

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.get_db import get_db
from app.logging import get_logger
from app.models import User

logger = get_logger(__name__)

bearer = HTTPBearer()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> User:
    """Get current authenticated user from Firebase token.

    Verifies the Firebase ID token, looks up or creates the user in the
    database, and returns the user object. Automatically creates new users
    on first authentication.

    Args:
        db: Database session from dependency injection.
        credentials: HTTP Bearer token credentials from request header.

    Returns:
        User: Authenticated user object from database.

    Raises:
        HTTPException: 401 if token is invalid or expired.
        HTTPException: 403 if user account is inactive.
    """
    # Extract token from request header
    token = credentials.credentials

    # Verify the token with Firebase
    try:
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token)
    except InvalidIdTokenError as e:
        logger.error("token.invalid", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except ExpiredIdTokenError as e:
        logger.error("token.expired", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
    except Exception as e:
        logger.error("token.verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

    # Look up user in the database
    stmt = select(User).filter(User.firebase_uid == decoded_token['uid'])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Create a new user
        logger.info(
            "user.created",
            firebase_uid=decoded_token['uid'],
            email=decoded_token.get('email')
        )
        stmt = insert(User).values(
            firebase_uid=decoded_token['uid'],
            email=decoded_token.get('email'),
        ).returning(User)
        result = await db.execute(stmt)
        await db.flush()
        user = result.scalar_one()
    elif not user.is_active:
        logger.warning("user.inactive", firebase_uid=decoded_token['uid'])
        raise HTTPException(
            status_code=403,
            detail="User inactive"
        )

    return user

