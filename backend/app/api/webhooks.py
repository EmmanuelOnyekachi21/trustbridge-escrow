"""Webhook API endpoints.

This module handles incoming webhooks from payment providers like Flutterwave
for processing payment notifications and updating transaction status.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies.get_db import get_db
from app.logging import get_logger
from app.models.audit_logs import AuditLog
from app.models.enums import TransactionStatus
from app.models.transactions import Transaction
from app.models.wallets import Wallet
from app.services.flutter_wave import (
    FlutterWaveService,
    FlutterwaveVerificationError,
)

from app.dependencies.get_flutterwave import get_flutterwave_service

router = APIRouter()
logger = get_logger(__name__)


def verify_flutterwave_signature(signature: str, secret: str) -> bool:
    """Verify Flutterwave webhook signature.

    Args:
        signature: verif-hash header from request.
        secret: Your webhook secret from config.

    Returns:
        True if signature is valid, False otherwise.
    """
    return hmac.compare_digest(signature, secret)


@router.post('/flutterwave')
async def flutterwave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterWaveService = Depends(get_flutterwave_service)
):
    """Handle Flutterwave payment webhooks.

    This endpoint is called by Flutterwave when payment events occur.
    It is NOT authenticated via JWT - security is via signature verification.

    Args:
        request: FastAPI request object containing webhook payload.
        db: Database session from dependency injection.

    Returns:
        Dictionary with status and message.

    Raises:
        HTTPException: 401 if signature is missing or invalid.
    """
    signature = request.headers.get('verif-hash')
    if not signature:
        logger.error("Webhook signature verification failed")
        raise HTTPException(401, "Missing signature")

    # Verify signature
    if not verify_flutterwave_signature(
        signature,
        settings.flutterwave_webhook_secret
    ):
        logger.error("Webhook signature verification failed")
        raise HTTPException(401, "Invalid signature")

    # Parse webhook body
    payload = await request.json()

    # For debugging. Would remove in production.
    logger.info(f"Received Payload: {payload}")

    # Check event type
    event_type = payload.get('event.type')

    # Only care about successful charges
    if not event_type:
        logger.warning("Webhook missing event.type field")
        return {"status": "ignored", "reason": "missing_event_type"}

    logger.info(f"Webhook event type: {event_type}")

    # Extract payment data
    tx_ref = payload.get('txRef')
    flw_ref = payload.get('flwRef')
    webhook_currency = payload.get('currency')
    payment_status = payload.get('status')

    if not tx_ref:
        logger.error("Webhook missing tx_ref")
        return {'status': 'error', 'message': 'Missing txRef'}

    # Only process successful payments
    if payment_status != 'successful':
        logger.info(
            f"Ignoring non-successful payment: {tx_ref} "
            f"with status: {payment_status}"
        )
        return {"status": "ignored", "reason": f"status__{payment_status}"}

    # Look up transaction
    stmt = (
        select(Transaction)
        .where(Transaction.reference == tx_ref)
        .with_for_update()  # Pessimistic locking to prevent race condition
    )
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()

    if not transaction:
        logger.error(f"Transaction not found for reference: {tx_ref}")
        return {
            "status": "error",
            "message": "Transaction not found"
        }

    # Idempotency Guard
    if transaction.status == TransactionStatus.FUNDED:
        logger.info(f"Transaction already processed: {tx_ref}")
        return {
            "status": "success",
            "message": "Transaction already processed"
        }

    # Verify payment with Flutterwave API
    try:
        verified_data = await flutterwave_service.verify_payment(tx_ref)
        logger.info(
            f"Flutterwave Service returned verified data: {verified_data}"
        )
    except FlutterwaveVerificationError as e:
        logger.error(f"Payment verification failed for {tx_ref}: {e}")
        return {'status': 'verification_failed'}

    # Validate Payment status
    if verified_data.get('status') != 'successful':
        logger.error(
            f"Payment verification failed for {tx_ref}: {verified_data}"
        )
        return {'status': 'payment_not_successful'}

    # Amount validation to prevent any fraud attempt
    verified_amount = Decimal(verified_data.get('amount'))
    verified_currency = verified_data.get('currency')

    if verified_amount != transaction.amount:
        logger.error(
            f"Amount mismatch for {tx_ref}: "
            f"expected {transaction.amount}, got {verified_amount}"
        )
        return {'status': 'amount_mismatch'}

    if verified_currency != transaction.currency.value:
        logger.error(
            f"Currency mismatch for {tx_ref}: "
            f"expected {transaction.currency.value}, got {verified_currency}"
        )
        return {"status": "currency_mismatch"}

    # Update transaction to FUNDED
    transaction.status = TransactionStatus.FUNDED
    transaction.funded_at = datetime.now(timezone.utc)
    transaction.flutterwave_tx_id = flw_ref

    # Update the buyer's wallet locked_balance
    # Get or create wallet for buyer in this currency
    wallet_stmt = (
        select(Wallet)
        .where(Wallet.user_id == transaction.buyer_id)
        .where(Wallet.currency == transaction.currency)
        .with_for_update()
    )
    wallet_result = await db.execute(wallet_stmt)
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        # Create wallet if doesn't exist
        wallet = Wallet(
            user_id=transaction.buyer_id,
            currency=transaction.currency,
            balance=Decimal("0.00"),
            locked_balance=Decimal("0.00")
        )
        db.add(wallet)
        await db.flush()

    # Increase locked balance (funds are in escrow)
    wallet.locked_balance += transaction.amount

    # Write audit log
    audit_log = AuditLog(
        transaction_id=transaction.id,
        actor_id=transaction.buyer_id,
        action="transaction.funded",
        extra_data={
            "amount": str(transaction.amount),
            "currency": transaction.currency.value,
            "flutterwave_reference": flw_ref,
            "event_type": event_type
        }
    )
    db.add(audit_log)

    # Commit everything
    await db.commit()

    logger.info(
        f"Transaction {tx_ref} funded successfully. "
        f"Amount: {transaction.amount} {transaction.currency.value}"
    )

    return {"status": "success"}


