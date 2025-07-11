import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.user import User


@pytest.mark.asyncio
async def test_create_search_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/searches",
        json={
            "name": "Test Search",
            "query": "vinyl records",
            "platform": "EBAY",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_search_with_auth(client: AsyncClient, db_session: AsyncSession):
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Create search
    response = await client.post(
        "/api/v1/searches",
        json={
            "name": "Rare Jazz Vinyl",
            "query": "blue note jazz vinyl",
            "platform": "BOTH",
            "check_interval_hours": 12,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Rare Jazz Vinyl"
    assert data["query"] == "blue note jazz vinyl"
    assert data["platform"] == "BOTH"
    assert data["check_interval_hours"] == 12


@pytest.mark.asyncio
async def test_create_search_with_preferences(client: AsyncClient, db_session: AsyncSession):
    # Create a test user
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Create search with preferences
    response = await client.post(
        "/api/v1/searches",
        json={
            "name": "High Quality Jazz",
            "query": "blue note jazz mint",
            "platform": "DISCOGS",
            "check_interval_hours": 6,
            "min_record_condition": "NM",
            "min_sleeve_condition": "VG+",
            "seller_location_preference": "US",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "High Quality Jazz"
    assert data["query"] == "blue note jazz mint"
    assert data["platform"] == "DISCOGS"
    assert data["check_interval_hours"] == 6
    assert data["min_record_condition"] == "NM"
    assert data["min_sleeve_condition"] == "VG+"
    assert data["seller_location_preference"] == "US"
