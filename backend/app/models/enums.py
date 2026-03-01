"""Database enumerations for TrustBridge.

This module defines all enum types used across database models.
These enums enforce valid states at the database level.
"""

import enum


class TransactionStatus(str, enum.Enum):
    """Transaction lifecycle states.

    States:
        PENDING: Transaction created but not yet funded.
        FUNDED: Buyer has paid, funds held in escrow.
        ACTIVE: Same as FUNDED (escrow is active).
        RELEASED: Funds released to vendor.
        DISPUTED: Transaction under dispute.
        REFUNDED: Funds returned to buyer.
    """

    PENDING = "PENDING"
    FUNDED = "FUNDED"
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    DISPUTED = "DISPUTED"
    REFUNDED = "REFUNDED"


class Currency(str, enum.Enum):
    """Supported currencies.

    Currencies:
        NGN: Nigerian Naira.
        GHS: Ghanaian Cedi.
        KES: Kenyan Shilling.
        USD: US Dollar.
    """

    NGN = "NGN"
    GHS = "GHS"
    KES = "KES"
    USD = "USD"
