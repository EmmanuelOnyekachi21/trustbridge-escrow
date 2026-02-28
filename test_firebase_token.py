#!/usr/bin/env python3
"""Firebase custom token generator for testing.

Quick script to generate a Firebase custom token for testing API endpoints.
Run this to get a token you can use in Postman or other API clients.

Usage:
    python test_firebase_token.py [uid]

If no UID is provided, uses a default test UID.
"""

import sys

import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase Admin
cred = credentials.Certificate("./trustbridge.json")
firebase_admin.initialize_app(cred)

# Get the UID from command line or use a default
uid = sys.argv[1] if len(sys.argv) > 1 else "eqEzOrpYILTh8YELczHzGMKlc1h2"

# Create a custom token
custom_token = auth.create_custom_token(uid)

print("\n" + "=" * 60)
print("Firebase Custom Token Generated!")
print("=" * 60)
print(f"\nUID: {uid}")
print(f"\nToken (use this in Postman):\n{custom_token.decode('utf-8')}")
print("\n" + "=" * 60)
print("\nIn Postman:")
print("  Authorization → Type: Bearer Token")
print("  Token: <paste the token above>")
print("=" * 60 + "\n")
