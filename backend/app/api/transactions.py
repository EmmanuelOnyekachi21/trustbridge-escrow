"""Transaction API endpoints.

This module provides endpoints for creating and managing escrow transactions
including payment initiation.
"""

import random
import string
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.get_current_user import get_current_user
from app.dependencies.get_db import get_db
from app.logging import get_logger
from app.models.audit_logs import AuditLog
from app.models.enums import TransactionStatus
from app.models.transactions import Transaction
from app.models.users import User
from app.schemas.transactions import (
    PaymentInitiationResponse,
    TransactionCreateRequest,
    TransactionResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    request: TransactionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Transaction:
    """Create a new escrow transaction.

    Flow:
        1. Validate vendor exists and is active
        2. Prevent self-transactions
        3. Generate unique reference
        4. Create transaction in DB
        5. Write audit log
        6. Return transaction details

    Args:
        request: Transaction creation request data.
        current_user: Authenticated user from dependency injection.
        db: Database session from dependency injection.

    Returns:
        Created transaction object.

    Raises:
        HTTPException: 404 if vendor not found.
        HTTPException: 400 if vendor inactive or self-transaction.
        HTTPException: 500 if reference generation fails.
    """
    vendor = await db.get(User, request.vendor_id)

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if not vendor.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive")

    if current_user.id == vendor.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transact with yourself"
        )

    try:
        # Generate unique reference
        reference = await generate_transaction_reference(db)
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail="Could not generate transaction reference"
        ) from e

    # Create transaction
    transaction = Transaction(
        reference=reference,
        buyer_id=current_user.id,
        vendor_id=vendor.id,
        amount=request.amount,
        currency=request.currency,
        description=request.description,
        status=TransactionStatus.PENDING
    )

    db.add(transaction)
    await db.flush()  # Get the ID without committing yet

    audit_log = AuditLog(
        transaction_id=transaction.id,
        actor_id=current_user.id,
        action="transaction.created",
        extra_data={
            "amount": str(transaction.amount),
            "currency": transaction.currency.value,
            "vendor_id": str(request.vendor_id)
        }
    )

    db.add(audit_log)
    await db.commit()
    await db.refresh(transaction)

    return transaction


async def generate_transaction_reference(db: AsyncSession) -> str:
    """Generate unique transaction reference.

    Format: TB-YYYYMMDD-XXXXXX
    Example: TB-20260321-A1B2C3

    Args:
        db: Database session for uniqueness check.

    Returns:
        Unique transaction reference string.

    Raises:
        RuntimeError: If unable to generate unique reference after max retries.
    """
    max_retries = 10

    for attempt in range(max_retries):
        date_part = datetime.utcnow().strftime("%Y%m%d")
        # Generate 6 random chars (A-Z, 0-9)
        chars = string.ascii_uppercase + string.digits
        random_part = ''.join(random.choices(chars, k=6))
        reference = f"TB-{date_part}-{random_part}"

        stmt = select(Transaction).where(Transaction.reference == reference)
        results = await db.execute(stmt)
        if results.scalar_one_or_none() is None:
            return reference

    # If we get here, we failed to generate unique ref
    logger.error(
        "Failed to generate unique transaction reference",
        attempts=max_retries
    )
    raise RuntimeError("Reference generation failed")

@router.post("/{transaction_id}/pay", response_model=PaymentInitiationResponse)
async def pay_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiate payment for a transaction.
    This endpoint would integrate with a payment provider

    Returns Flutterwave checkout URL. Idempotent - calling twice
    returns the same URL without createing duplcate charges.
    """
    from app.services.flutter_wave import FlutterWaveService, FlutterwavePaymentError
    from app.config import settings
    from sqlalchemy import update
    from app.logging import get_logger    
    
    logger = get_logger(__name__)


    # Checking if transaction ID already exists
    stmt = (
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .with_for_update()
    )
    result = await db.execute(stmt)

    transaction = result.scalar_one_or_none()
    
    if transaction is None:
        raise HTTPException(
            status_code=400,
            detail="Transaction ID does not exist"
        )
    else:
               
        # Check state of transaction ID
        if transaction.status != TransactionStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Transaction already funded or released"
            )
        
        # Check if current user is the buyer
        if transaction.buyer_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the buyer can initiate payment"
            )
        
        # Idempotency check: if flutterwave_tx_id exists, payment already initiated
        if transaction.payment_link:
            return PaymentInitiationResponse(
                transaction_id=transaction.id,
                payment_link=transaction.payment_link,
                message="Payment already initiated"
            )
        
        flutterwave_service = FlutterWaveService()

        # build redirect URL (where Flutterwave sends user after payment)
        frontend_url = f"{settings.frontend_url}/transactions/{transaction.id}/confirm"

        try:
            payment_link = await flutterwave_service.initiate_payment(
                transaction=transaction,
                user=current_user,
                redirect_url=frontend_url
            )
            logger.info(f"Payment initiated for {transaction.reference}")
        except FlutterwavePaymentError as e:
            logger.error(f"Failed to initiate payment: {e}")
            raise HTTPException(500, "Failed to initiate payment. Please try again.")


        stmt = (
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(
                payment_link=payment_link
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        await db.refresh(transaction)

        return PaymentInitiationResponse(
            transaction_id=transaction.id,
            payment_link=payment_link,
            message="Payment initiated successfully"
        )


    
    



@router.post("/{transaction_id}/pay", response_model=PaymentInitiationResponse)
async def pay_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate payment for a transaction.

    This endpoint integrates with Flutterwave payment provider to generate
    a checkout URL. Idempotent - calling twice returns the same URL without
    creating duplicate charges.

    Args:
        transaction_id: UUID of the transaction to pay for.
        db: Database session from dependency injection.
        current_user: Authenticated user from dependency injection.

    Returns:
        PaymentInitiationResponse with payment link and message.

    Raises:
        HTTPException: 400 if transaction not found or invalid state.
        HTTPException: 403 if user is not the buyer.
        HTTPException: 500 if payment initiation fails.
    """
    from app.config import settings
    from app.services.flutter_wave import (
        FlutterWaveService,
        FlutterwavePaymentError,
    )
    from sqlalchemy import update

    # Check if transaction ID already exists
    stmt = (
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .with_for_update()
    )
    result = await db.execute(stmt)

    transaction = result.scalar_one_or_none()

    if transaction is None:
        raise HTTPException(
            status_code=400,
            detail="Transaction ID does not exist"
        )

    # Check state of transaction ID
    if transaction.status != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Transaction already funded or released"
        )

    # Check if current user is the buyer
    if transaction.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the buyer can initiate payment"
        )

    # Idempotency check: if payment_link exists, payment already initiated
    if transaction.payment_link:
        return PaymentInitiationResponse(
            transaction_id=transaction.id,
            payment_link=transaction.payment_link,
            message="Payment already initiated"
        )

    flutterwave_service = FlutterWaveService()

    # Build redirect URL (where Flutterwave sends user after payment)
    frontend_url = (
        f"{settings.frontend_url}/transactions/{transaction.id}/confirm"
    )

    try:
        payment_link = await flutterwave_service.initiate_payment(
            transaction=transaction,
            user=current_user,
            redirect_url=frontend_url
        )
        logger.info(f"Payment initiated for {transaction.reference}")
    except FlutterwavePaymentError as e:
        logger.error(f"Failed to initiate payment: {e}")
        raise HTTPException(500, "Failed to initiate payment. Please try again.")

    stmt = (
        update(Transaction)
        .where(Transaction.id == transaction_id)
        .values(payment_link=payment_link)
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(transaction)

    return PaymentInitiationResponse(
        transaction_id=transaction.id,
        payment_link=payment_link,
        message="Payment initiated successfully"
    )
