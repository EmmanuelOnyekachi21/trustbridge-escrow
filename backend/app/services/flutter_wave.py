"""Flutterwave payment service.

This service handles all interactions with Flutterwave's API for payment
collection and verification.
"""

from decimal import Decimal
from typing import Any, Dict

import httpx

from app.config import settings
from app.logging import get_logger
from app.models.transactions import Transaction
from app.models.users import User

logger = get_logger(__name__)


class FlutterwaveError(Exception):
    """Base exception for Flutterwave-related errors."""

    pass


class FlutterwavePaymentError(FlutterwaveError):
    """Raised when payment initiation fails."""

    pass


class FlutterwaveVerificationError(FlutterwaveError):
    """Raised when payment verification fails."""

    pass


class FlutterWaveService:
    """Service for Flutterwave payment operations.

    Handles payment initiation and verification with proper error handling
    and logging.
    """

    def __init__(self):
        """Initialize Flutterwave service with API credentials."""
        self.base_url = settings.flutterwave_base_url
        self.secret_key = settings.flutterwave_secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def initiate_payment(
        self,
        transaction: Transaction,
        user: User,
        redirect_url: str
    ) -> str:
        """Initiate a payment with Flutterwave.

        Args:
            transaction: The transaction to create payment for.
            user: The buyer initiating payment.
            redirect_url: URL to redirect user after payment.
            
        Returns:
            The hosted checkout URL where buyer completes payment.
            
        Raises:
            FlutterwavePaymentError: If payment initiation fails.
        """

        # Build the payment payload
        payload = {
            "tx_ref": transaction.reference,
            "amount": str(transaction.amount),
            "currency": transaction.currency.value,
            "redirect_url": redirect_url,
            "customer": {
                "email": user.email,
                "name": user.email
            },
            "customizations": {
                "title": "Trustbridge Escrow Payment",
                "description": transaction.description,
                # "logo": "https://yourdomain.com/logo.png"
            },
            # Meta field lets you pass custom data
            # that comes back in webhook
            "meta": {
                "transaction_id": str(transaction.id),
                "buyer_id": str(user.id)
            }
        }

        logger.info(
            f"Initializing Flutterwave payment for transaction {transaction.reference}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                data = response.json()

                # Flutterwave returns payment link in data.link
                if data.get('status') == 'success':
                    payment_link = data['data']['link']

                    logger.info(
                        f"Payment link generated for {transaction.reference}: {payment_link}"
                    )
                    return payment_link
                
                else:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(
                        f"Flutterwave payment initiation failed: {error_msg}"
                    )
                    raise FlutterwavePaymentError(error_msg)
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error initiating payment for {transaction.reference}: {e}"
            )
            raise FlutterwavePaymentError(f"Payment initiation failed: {str(e)}")
        
    async def verify_payment(
        self,
        transaction_reference: str
    ) -> Dict[str, Any]:
        """Verify a payment with Flutterwave.

        This should be called in the webhook handler to confirm payment
        actually happened on Flutterwave's side before updating your DB.

        Args:
            transaction_reference: Your tx_ref used during initiation.

        Returns:
            Dictionary containing payment details from Flutterwave:
                - status: Payment status (successful, failed, etc)
                - amount: Amount paid
                - currency: Currency code
                - tx_ref: Your transaction reference
                - flw_ref: Flutterwave's reference

        Raises:
            FlutterwaveVerificationError: If verification fails.
        """
        logger.info(f"Verifying payment for transaction {transaction_reference}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Flutterwave verify endpoint uses tx_ref in URL
                response = await client.get(
                    f"{self.base_url}/transactions/verify_by_reference",
                    params={'tx_ref': transaction_reference},
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

                if data.get('status') == 'success':
                    payment_data = data['data']
                    logger.info(
                        f"Payment verified for {transaction_reference}: "
                        f"status={payment_data.get('status')}, "
                        f"amount={payment_data.get('amount')}"
                    )

                    return payment_data
                else:
                    error_msg = data.get("message", "Verification failed")
                    logger.error(
                        f"Payment verification failed for "
                        f"{transaction_reference}: {error_msg}"
                    )
                    raise FlutterwaveVerificationError(error_msg)
        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error verifying payment {transaction_reference}: {e}"
            )
            raise FlutterwaveVerificationError(
                f"Verification request failed: {str(e)}"
            )

    