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


@pytest.mark.asyncio
async def test_get_searches(client: AsyncClient, db_session: AsyncSession):
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
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple searches
    searches = [
        {"name": "Jazz Records", "query": "jazz vinyl", "platform": "DISCOGS"},
        {"name": "Rock Albums", "query": "rock vinyl", "platform": "EBAY"},
        {"name": "Classical", "query": "classical music", "platform": "BOTH"},
    ]

    for search in searches:
        await client.post("/api/v1/searches", json=search, headers=headers)

    # Get all searches
    response = await client.get("/api/v1/searches", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert {s["name"] for s in data} == {"Jazz Records", "Rock Albums", "Classical"}


@pytest.mark.asyncio
async def test_delete_search(client: AsyncClient, db_session: AsyncSession):
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
    headers = {"Authorization": f"Bearer {token}"}

    # Create a search
    create_response = await client.post(
        "/api/v1/searches",
        json={
            "name": "Test Delete",
            "query": "test query",
            "platform": "BOTH",
        },
        headers=headers,
    )
    search_id = create_response.json()["id"]

    # Delete the search
    delete_response = await client.delete(f"/api/v1/searches/{search_id}", headers=headers)
    assert delete_response.status_code == 200

    # Verify it's deleted
    get_response = await client.get("/api/v1/searches", headers=headers)
    searches = get_response.json()
    assert len(searches) == 0


@pytest.mark.asyncio
async def test_run_search(client: AsyncClient, db_session: AsyncSession):
    from unittest.mock import patch

    # Mock the Celery task to avoid Redis connection
    with patch("src.services.search.run_search_task") as mock_task:
        mock_task.delay.return_value = "task-id-123"

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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a search
        create_response = await client.post(
            "/api/v1/searches",
            json={
                "name": "Test Run",
                "query": "test query",
                "platform": "DISCOGS",
            },
            headers=headers,
        )
        search_id = create_response.json()["id"]

        # Run the search
        run_response = await client.post(f"/api/v1/searches/{search_id}/run", headers=headers)
        assert run_response.status_code == 200
        assert "message" in run_response.json()

        # Verify the Celery task was called
        mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_get_search_results(client: AsyncClient, db_session: AsyncSession):
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
    headers = {"Authorization": f"Bearer {token}"}

    # Create a search
    create_response = await client.post(
        "/api/v1/searches",
        json={
            "name": "Test Results",
            "query": "test query",
            "platform": "BOTH",
        },
        headers=headers,
    )
    search_id = create_response.json()["id"]

    # Get search results (should be empty initially)
    results_response = await client.get(f"/api/v1/searches/{search_id}/results", headers=headers)
    assert results_response.status_code == 200
    assert results_response.json() == []


@pytest.mark.asyncio
async def test_update_search(client: AsyncClient, db_session: AsyncSession):
    """Test updating a saved search with partial data."""
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
    headers = {"Authorization": f"Bearer {token}"}

    # Create a search
    create_response = await client.post(
        "/api/v1/searches",
        json={
            "name": "Original Search",
            "query": "original query",
            "platform": "DISCOGS",
            "check_interval_hours": 24,
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    search_data = create_response.json()
    search_id = search_data["id"]

    # Update with partial data
    update_response = await client.put(
        f"/api/v1/searches/{search_id}",
        json={
            "name": "Updated Search",
            "check_interval_hours": 12,
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()

    # Verify changes
    assert updated_data["name"] == "Updated Search"
    assert updated_data["check_interval_hours"] == 12
    assert updated_data["query"] == "original query"  # Should remain unchanged
    assert updated_data["platform"] == "DISCOGS"  # Should remain unchanged


@pytest.mark.asyncio
async def test_update_search_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test updating a non-existent search."""
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
    headers = {"Authorization": f"Bearer {token}"}

    # Try to update non-existent search
    from uuid import uuid4

    fake_id = uuid4()
    update_response = await client.put(
        f"/api/v1/searches/{fake_id}",
        json={"name": "Updated Search"},
        headers=headers,
    )
    assert update_response.status_code == 404


@pytest.mark.asyncio
async def test_update_search_unauthorized(client: AsyncClient, db_session: AsyncSession):
    """Test updating another user's search."""
    # Create two test users
    user1 = User(
        email="user1@example.com",
        hashed_password=get_password_hash("testpassword123"),
    )
    user2 = User(
        email="user2@example.com",
        hashed_password=get_password_hash("testpassword123"),
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()

    # Login as user1 and create a search
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "user1@example.com",
            "password": "testpassword123",
        },
    )
    token1 = login_response.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    create_response = await client.post(
        "/api/v1/searches",
        json={
            "name": "User1 Search",
            "query": "user1 query",
            "platform": "DISCOGS",
        },
        headers=headers1,
    )
    search_id = create_response.json()["id"]

    # Login as user2 and try to update user1's search
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "user2@example.com",
            "password": "testpassword123",
        },
    )
    token2 = login_response.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    update_response = await client.put(
        f"/api/v1/searches/{search_id}",
        json={"name": "Hijacked Search"},
        headers=headers2,
    )
    assert update_response.status_code == 404  # Should appear as not found for security
