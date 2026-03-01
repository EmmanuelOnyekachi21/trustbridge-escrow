"""Audit log database model.

This module defines the AuditLog model which provides an immutable,
append-only audit trail for all critical actions in TrustBridge.

CRITICAL: This table is APPEND-ONLY. No updates, no deletes, ever.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditLog(Base):
    """Immutable audit log for all critical system actions.

    Every state change, money movement, and admin action writes a new
    row to this table. Records are never updated or deleted.

    This provides:
        - Complete audit trail for compliance
        - Forensic investigation capability
        - Regulatory reporting data
        - Dispute resolution evidence

    Attributes:
        id: Unique log entry identifier (UUID).
        transaction_id: Related transaction (nullable for user-level events).
        actor_id: User who performed the action.
        action: Action type (e.g. 'transaction.funded', 'user.kyc_approved').
        extra_data: JSON object with additional context (amounts, old/new
            state, IP, etc).
        created_at: When this action occurred (immutable).

    Note:
        No updated_at column - audit logs are never modified.
    """

    __tablename__ = "audit_logs"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Related entities
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    
    # Flexible metadata storage - using 'extra_data' instead of 'metadata' (reserved name)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Immutable timestamp - no updated_at!
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        back_populates="audit_logs"
    )
    
    actor: Mapped["User"] = relationship(
        "User",
        back_populates="audit_logs"
    )
    
    def __repr__(self) -> str:
        """Return string representation of AuditLog.

        Returns:
            String showing action, actor, and timestamp.
        """
        return (
            f"<AuditLog {self.action} by {self.actor_id} "
            f"at {self.created_at}>"
        )
