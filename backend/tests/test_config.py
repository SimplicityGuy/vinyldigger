"""Tests for config endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


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


@pytest.mark.asyncio
async def test_update_preferences(client: AsyncClient, db_session: AsyncSession):
    """Test updating user preferences."""
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

    # Update preferences
    response = await client.put(
        "/api/v1/config/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "min_record_condition": "VG",
            "min_sleeve_condition": "G+",
            "seller_location_preference": "UK",
            "check_interval_hours": 12,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Check updated values
    assert data["min_record_condition"] == "VG"
    assert data["min_sleeve_condition"] == "G+"
    assert data["seller_location_preference"] == "UK"
    assert data["check_interval_hours"] == 12


@pytest.mark.asyncio
async def test_update_preferences_partial(client: AsyncClient, db_session: AsyncSession):
    """Test partially updating user preferences."""
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

    # Update only some preferences
    response = await client.put(
        "/api/v1/config/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "check_interval_hours": 6,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Check that non-updated values remain default
    assert data["min_record_condition"] == "VG+"
    assert data["min_sleeve_condition"] == "VG+"
    assert data["seller_location_preference"] == "US"
    assert data["check_interval_hours"] == 6
