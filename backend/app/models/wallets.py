"""Wallet database model.

This module defines the Wallet model which tracks user balances per currency.
Each user can have one wallet per currency.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Currency


class Wallet(Base):
    """Wallet model for tracking user balances.

    Each user has one wallet per currency. Wallets track both available
    balance and locked balance (funds held in active escrow transactions).

    Key features:
        - One wallet per user per currency (enforced by unique constraint)
        - Separate tracking of available vs locked funds
        - Numeric type for all money fields (never float)

    Attributes:
        id: Unique wallet identifier (UUID).
        user_id: Foreign key to user who owns this wallet.
        currency: Currency code (NGN, GHS, KES, USD).
        balance: Available balance (can be withdrawn/used).
        locked_balance: Funds locked in active escrow transactions.
        created_at: Wallet creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "wallets"
    
    # Unique constraint: one wallet per user per currency
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="uq_user_currency"),
    )
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Owner
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Currency
    currency: Mapped[Currency] = mapped_column(
        nullable=False
    )
    
    # Balance fields - NEVER use float, always Numeric
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=Decimal("0.00000000")
    )
    
    locked_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        default=Decimal("0.00000000")
    )
    
    # Standard timestamps
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
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="wallets"
    )
    
    def __repr__(self) -> str:
        """Return string representation of Wallet.

        Returns:
            String showing user ID, currency, balance, and locked balance.
        """
        return (
            f"<Wallet {self.user_id} {self.currency.value} "
            f"balance={self.balance} locked={self.locked_balance}>"
        )
