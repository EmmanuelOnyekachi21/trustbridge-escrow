"""Authentication API endpoints.

This module provides authentication-related endpoints including user
profile retrieval for authenticated users.
"""

from fastapi import APIRouter, Depends

from app.dependencies.get_current_user import get_current_user
from app.models import User
from app.schemas.users import UserResponse

router = APIRouter()


@router.get('/me')
async def get_user(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current authenticated user profile.

    Returns the profile information for the currently authenticated user
    based on their Firebase token.

    Args:
        current_user: Authenticated user from dependency injection.

    Returns:
        UserResponse: User profile data including ID, email, role, and status.
    """
    return UserResponse.model_validate(current_user)
