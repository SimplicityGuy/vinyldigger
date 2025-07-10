"""Tests for config endpoints including API key management."""

from datetime import datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_api_keys_empty(client: AsyncClient, db_session: AsyncSession):
    """Test getting API keys when none exist."""
    # Register and login
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "username": "testuser",
        },
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get API keys
    response = await client.get(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # API returns a list of APIKeyResponse objects
    assert data == []


@pytest.mark.asyncio
async def test_update_api_keys_serialization(client: AsyncClient, db_session: AsyncSession):
    """Test that API key update properly serializes UUID and datetime fields."""
    # Register and login
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "username": "testuser",
        },
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Update Discogs API key
    response = await client.put(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service": "discogs",
            "key": "test-discogs-token-123",
        },
    )

    # This is the fix we're testing - previously this would fail with validation errors
    assert response.status_code == 200
    data = response.json()

    # Verify the response structure
    assert "id" in data
    assert "created_at" in data
    assert "service" in data
    assert data["service"] == "discogs"

    # Verify that id is a valid UUID string
    try:
        UUID(data["id"])
    except ValueError:
        pytest.fail("id field is not a valid UUID string")

    # Verify that created_at is a valid datetime string
    try:
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("created_at field is not a valid ISO datetime string")

    # Now update eBay API key with both app_id and secret
    response = await client.put(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service": "ebay",
            "key": "test-ebay-app-id-456",
            "secret": "test-ebay-cert-id-789",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ebay"

    # Verify both keys are saved by getting all API keys
    response = await client.get(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    api_keys = response.json()
    assert len(api_keys) == 2

    # Find the services in the response
    services = {key["service"] for key in api_keys}
    assert services == {"discogs", "ebay"}


@pytest.mark.asyncio
async def test_update_api_keys_partial(client: AsyncClient, db_session: AsyncSession):
    """Test updating only some API keys."""
    # Register and login
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "username": "testuser",
        },
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Add only Discogs token
    response = await client.put(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service": "discogs",
            "key": "new-discogs-token",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "discogs"

    # Verify only one key exists
    response = await client.get(
        "/api/v1/config/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    api_keys = response.json()
    assert len(api_keys) == 1
    assert api_keys[0]["service"] == "discogs"


@pytest.mark.asyncio
async def test_get_preferences(client: AsyncClient, db_session: AsyncSession):
    """Test getting user preferences."""
    # Register and login
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "username": "testuser",
        },
    )
    assert register_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "TestPassword123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get preferences
    response = await client.get(
        "/api/v1/config/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Check default values based on PreferencesResponse model
    assert data["min_record_condition"] == "VG+"
    assert data["min_sleeve_condition"] == "VG+"
    assert data["seller_location_preference"] == "US"
    assert data["check_interval_hours"] == 24
