"""Tests for user-related API endpoints."""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.main import app
from src.models.user import User


class TestUserEndpoints:
    """Test suite for user-related endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    @pytest.fixture
    def authenticated_client(self, client: AsyncClient, mock_user):
        """Create authenticated client with mock user."""

        async def mock_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user
        yield client
        app.dependency_overrides.pop(get_current_user, None)

    async def test_update_user_success(self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user):
        """Test successful user update."""
        db_session.add(mock_user)
        await db_session.commit()

        update_data = {"email": "newemail@example.com"}
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newemail@example.com"
        assert data["id"] == str(mock_user.id)

    async def test_update_user_duplicate_email(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user
    ):
        """Test user update with duplicate email."""
        # Add current user
        db_session.add(mock_user)

        # Add another user with target email
        other_user = User(
            id=uuid4(),
            email="existing@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.commit()

        update_data = {"email": "existing@example.com"}
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]

    async def test_update_user_same_email(self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user):
        """Test user update with same email (no change)."""
        db_session.add(mock_user)
        await db_session.commit()

        update_data = {"email": mock_user.email}
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == mock_user.email

    async def test_update_user_invalid_email(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user
    ):
        """Test user update with invalid email format."""
        db_session.add(mock_user)
        await db_session.commit()

        update_data = {"email": "invalid-email"}
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_user_empty_email(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user
    ):
        """Test user update with empty email."""
        db_session.add(mock_user)
        await db_session.commit()

        update_data = {"email": ""}
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_current_user_info(self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user):
        """Test getting current user information."""
        db_session.add(mock_user)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == mock_user.email
        assert data["id"] == str(mock_user.id)
        assert "created_at" in data
        assert "updated_at" in data

    async def test_update_user_unauthenticated(self, client: AsyncClient):
        """Test user update without authentication."""
        update_data = {"email": "newemail@example.com"}
        response = await client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_user_unauthenticated(self, client: AsyncClient):
        """Test getting user info without authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_user_with_extra_fields(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, mock_user
    ):
        """Test user update with extra fields (should be ignored)."""
        db_session.add(mock_user)
        await db_session.commit()

        update_data = {
            "email": "newemail@example.com",
            "is_admin": True,  # Should be ignored
            "extra_field": "value",  # Should be ignored
        }
        response = await authenticated_client.put("/api/v1/auth/me", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newemail@example.com"
        assert "is_admin" not in data
        assert "extra_field" not in data
