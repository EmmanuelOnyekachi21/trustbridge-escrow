"""Transaction Pydantic schemas for request/response validation.

This module defines Pydantic models for transaction data serialization
and validation in API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Currency, TransactionStatus


class TransactionCreateRequest(BaseModel):
    """Transaction creation request schema.

    Attributes:
        vendor_id: UUID of the vendor receiving payment.
        amount: Transaction amount (must be positive).
        currency: Currency code for the transaction.
        description: Description of the transaction purpose.
    """

    vendor_id: UUID
    amount: Decimal = Field(..., gt=0)
    currency: Currency
    description: str


class TransactionResponse(BaseModel):
    """Transaction response schema for API endpoints.

    Attributes:
        id: Unique transaction identifier.
        reference: Human-readable transaction reference.
        buyer_id: UUID of the buyer.
        vendor_id: UUID of the vendor.
        amount: Transaction amount.
        currency: Currency code.
        status: Current transaction status.
        description: Transaction description.
        created_at: When transaction was created.
        updated_at: When transaction was last updated.
    """

    id: UUID
    reference: str
    buyer_id: UUID
    vendor_id: UUID
    amount: Decimal = Field(..., ge=0)
    currency: Currency
    status: TransactionStatus
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

    @field_validator('description')
    @classmethod
    def description_not_empty(cls, v):
        """Validate description is not empty.

        Args:
            v: Description value to validate.

        Returns:
            Stripped description string.

        Raises:
            ValueError: If description is empty or whitespace only.
        """
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class PaymentInitiationResponse(BaseModel):
    """Response schema when payment is initiated.

    Attributes:
        transaction_id: UUID of the transaction.
        payment_link: URL to payment checkout page.
        message: Status message for the user.
    """

    transaction_id: UUID
    payment_link: str
    message: str
