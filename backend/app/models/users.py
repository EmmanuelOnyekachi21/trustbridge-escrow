"""User database models.

This module defines the User model and related enumerations for the
application's user management system.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration.

    Defines the available roles for users in the system.
    """

    buyer = "buyer"
    vendor = "vendor"
    admin = "admin"


class User(Base):
    """User model for authentication and authorization.

    Represents a user in the system with Firebase authentication integration,
    role-based access control, and KYC verification status.

    Attributes:
        id: Unique user identifier (UUID).
        firebase_uid: Firebase authentication UID (unique).
        role: User role (buyer, vendor, or admin).
        email: User email address (unique, optional).
        is_active: Whether the user account is active.
        kyc_verified: Whether the user has completed KYC verification.
        created_at: Timestamp when user was created (set by database).
        updated_at: Timestamp when user was last updated (set by database).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True
    )
    firebase_uid: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        nullable=False,
        default=UserRole.buyer
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    kyc_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self) -> str:
        """Return string representation of User.

        Returns:
            String representation showing email and role.
        """
        return f"<User {self.email} ({self.role})>"
