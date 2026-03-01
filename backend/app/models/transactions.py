"""Transaction database model.

This module defines the Transaction model which represents escrow transactions
in the TrustBridge platform. Every transaction tracks money movement between
buyers and vendors with full audit trail support.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Currency, TransactionStatus

if TYPE_CHECKING:
    from app.models.audit_logs import AuditLog
    from app.models.users import User


class Transaction(Base):
    """Transaction model for escrow operations.

    Represents a financial transaction between a buyer and vendor with
    escrow protection. Tracks all state changes, fees, and timestamps.

    Key features:
        - UUID primary key (non-guessable, safe for URLs)
        - Numeric type for all money fields (never float)
        - Optimistic locking via version column
        - Soft delete support via deleted_at
        - Full audit trail via timestamps

    Attributes:
        id: Unique transaction identifier (UUID).
        reference: Human-readable transaction ID (e.g. TB-20240101-XXXX).
        buyer_id: Foreign key to buyer user.
        vendor_id: Foreign key to vendor user.
        amount: Transaction amount (Numeric, 20 digits, 8 decimal places).
        currency: Currency code (NGN, GHS, KES, USD).
        status: Current transaction state (enum).
        description: Transaction description/purpose.
        platform_fee: TrustBridge platform fee (calculated at release).
        processor_fee: Payment processor fee (calculated at release).
        net_payout: Amount paid to vendor after fees.
        funded_at: When buyer funded the escrow.
        released_at: When funds were released to vendor.
        disputed_at: When dispute was raised.
        version: Optimistic locking counter.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
        deleted_at: Soft delete timestamp (null = not deleted).
    """

    __tablename__ = "transactions"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Human-readable reference
    reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Parties involved
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Money fields - NEVER use float, always Numeric
    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False
    )
    
    currency: Mapped[Currency] = mapped_column(
        nullable=False
    )
    
    # Transaction state
    status: Mapped[TransactionStatus] = mapped_column(
        nullable=False,
        default=TransactionStatus.PENDING,
        index=True
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Fee fields - calculated at release time
    platform_fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8),
        nullable=True
    )
    
    processor_fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8),
        nullable=True
    )
    
    net_payout: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8),
        nullable=True
    )
    
    # State change timestamps
    funded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    disputed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Optimistic locking
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
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
    
    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="transactions_as_buyer"
    )
    
    vendor: Mapped["User"] = relationship(
        "User",
        foreign_keys=[vendor_id],
        back_populates="transactions_as_vendor"
    )
    
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="transaction"
    )
    
    def __repr__(self) -> str:
        """Return string representation of Transaction.

        Returns:
            String showing reference, status, amount, and currency.
        """
        return (
            f"<Transaction {self.reference} {self.status.value} "
            f"{self.amount} {self.currency.value}>"
        )

