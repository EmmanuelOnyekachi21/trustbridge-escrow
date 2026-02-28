"""User Pydantic schemas for request/response validation.

This module defines Pydantic models for user data serialization and
validation in API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.users import UserRole


class UserResponse(BaseModel):
    """User response schema for API endpoints.

    Represents user data returned from API endpoints with all user
    attributes including authentication, role, and verification status.

    Attributes:
        id: Unique user identifier.
        firebase_uid: Firebase authentication UID.
        role: User role (buyer, vendor, or admin).
        email: User email address (optional).
        is_active: Whether the user account is active.
        kyc_verified: Whether the user has completed KYC verification.
        created_at: Timestamp when user was created.
        updated_at: Timestamp when user was last updated.
    """

    id: uuid.UUID
    firebase_uid: str
    role: UserRole
    email: Optional[str] = None
    is_active: bool
    kyc_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
