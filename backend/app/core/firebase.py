"""Firebase Admin SDK initialization and configuration.

This module handles Firebase Admin SDK initialization with support for
both file-based credentials (local development) and JSON string credentials
(production environments).
"""

import json

import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings


def _initialize_firebase() -> None:
    """Initialize Firebase Admin SDK once at startup.

    Supports both file-based (local dev) and JSON string (production)
    credentials. Prevents re-initialization if already initialized.

    Raises:
        RuntimeError: If no Firebase credentials are configured.
    """
    if firebase_admin._apps:
        # Already initialized — do nothing.
        # This guard matters during testing when modules reload.
        return

    if settings.firebase_service_account_path:
        cred = credentials.Certificate(settings.firebase_service_account_path)
    elif settings.firebase_service_account_json:
        service_account_dict = json.loads(
            settings.firebase_service_account_json
        )
        cred = credentials.Certificate(service_account_dict)
    else:
        raise RuntimeError(
            "No Firebase credentials found. "
            "Set FIREBASE_SERVICE_ACCOUNT_PATH or "
            "FIREBASE_SERVICE_ACCOUNT_JSON in your environment."
        )

    firebase_admin.initialize_app(cred)


def get_firebase_auth() -> auth:
    """Get the Firebase Auth module.

    Returns:
        Firebase Auth module for token verification and user management.

    Example:
        auth_module = get_firebase_auth()
        decoded_token = auth_module.verify_id_token(token)
    """
    return auth
