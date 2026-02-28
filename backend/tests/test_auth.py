"""Tests for authentication endpoints and Firebase token verification.

This module contains comprehensive tests for the authentication system
including token verification, user creation, and access control.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.database import Base
from app.dependencies.get_db import get_db
from app.main import app
from app.models import User

# Create in-memory SQLite database for testing (async)
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_firebase_token():
    """Mock Firebase token verification.

    Returns:
        Dictionary containing mock Firebase token claims.
    """
    return {
        'uid': 'test-firebase-uid-123',
        'email': 'test@example.com',
        'email_verified': True
    }


@pytest_asyncio.fixture
async def existing_user():
    """Create an existing user in the database.

    Returns:
        User: Created user instance.
    """
    async with TestingSessionLocal() as db:
        user = User(
            firebase_uid='existing-uid-456',
            email='existing@example.com',
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest.mark.asyncio
class TestAuthMe:
    """Test suite for /auth/me endpoint."""

    @patch('app.dependencies.get_current_user.auth.verify_id_token')
    async def test_get_me_with_new_user_creates_user(
        self,
        mock_verify,
        mock_firebase_token
    ):
        """Test that a new user is created when authenticated first time."""
        # Arrange
        mock_verify.return_value = mock_firebase_token

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer fake-token-123"}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == 'test@example.com'
        assert data['firebase_uid'] == 'test-firebase-uid-123'

        # Verify user was created in database
        async with TestingSessionLocal() as db:
            result = await db.execute(
                select(User).filter(
                    User.firebase_uid == 'test-firebase-uid-123'
                )
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.email == 'test@example.com'

    @patch('app.dependencies.get_current_user.auth.verify_id_token')
    async def test_get_me_with_existing_user_returns_user(
        self,
        mock_verify,
        existing_user
    ):
        """Test that existing user is returned without creating duplicate."""
        # Arrange
        mock_verify.return_value = {
            'uid': existing_user.firebase_uid,
            'email': existing_user.email
        }

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer fake-token-456"}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == existing_user.email
        assert data['firebase_uid'] == existing_user.firebase_uid

        # Verify no duplicate was created
        async with TestingSessionLocal() as db:
            result = await db.execute(
                select(func.count()).select_from(User).filter(
                    User.firebase_uid == existing_user.firebase_uid
                )
            )
            user_count = result.scalar()
            assert user_count == 1

    @patch('app.dependencies.get_current_user.auth.verify_id_token')
    async def test_get_me_with_invalid_token_returns_401(self, mock_verify):
        """Test that invalid token returns 401 Unauthorized."""
        # Arrange
        from firebase_admin.auth import InvalidIdTokenError
        mock_verify.side_effect = InvalidIdTokenError("Invalid token")

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid-token"}
            )

        # Assert
        assert response.status_code == 401
        assert "Invalid token" in response.json()['detail']

    @patch('app.dependencies.get_current_user.auth.verify_id_token')
    async def test_get_me_with_expired_token_returns_401(self, mock_verify):
        """Test that expired token returns 401 Unauthorized."""
        # Arrange
        from firebase_admin.auth import ExpiredIdTokenError
        mock_verify.side_effect = ExpiredIdTokenError("Token expired")

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer expired-token"}
            )

        # Assert
        assert response.status_code == 401
        assert "Token expired" in response.json()['detail']

    async def test_get_me_without_token_returns_403(self):
        """Test that missing token returns 403 Forbidden."""
        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/auth/me")

        # Assert
        assert response.status_code == 403

    @patch('app.dependencies.get_current_user.auth.verify_id_token')
    async def test_get_me_with_inactive_user_returns_403(self, mock_verify):
        """Test that inactive user cannot access the endpoint."""
        # Arrange - Create inactive user
        async with TestingSessionLocal() as db:
            inactive_user = User(
                firebase_uid='inactive-uid-789',
                email='inactive@example.com',
                is_active=False
            )
            db.add(inactive_user)
            await db.commit()

        mock_verify.return_value = {
            'uid': 'inactive-uid-789',
            'email': 'inactive@example.com'
        }

        # Act
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer fake-token"}
            )

        # Assert
        assert response.status_code == 403
        assert "inactive" in response.json()['detail'].lower()
