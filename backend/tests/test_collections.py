from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import get_password_hash
from src.models.user import User


@pytest.mark.asyncio
async def test_sync_all_collections(client: AsyncClient, db_session: AsyncSession):
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

    # Mock the celery task
    with patch("src.api.v1.endpoints.collections.sync_collection_task") as mock_task:
        mock_task.delay = MagicMock()

        # Sync all (both collection and want list)
        response = await client.post(
            "/api/v1/collections/sync",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Collection and want list sync queued successfully"

        # Verify task was called with correct user ID
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0]
        assert call_args[0] == str(user.id)  # user_id should be first argument


@pytest.mark.asyncio
async def test_sync_collection_only(client: AsyncClient, db_session: AsyncSession):
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

    # Mock the celery task
    with patch("src.api.v1.endpoints.collections.sync_collection_task") as mock_task:
        mock_task.delay = MagicMock()

        # Sync collection only
        response = await client.post(
            "/api/v1/collections/sync/collection",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Collection sync queued successfully"

        # Verify task was called with correct arguments
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args
        assert call_args[0][0] == str(user.id)
        assert call_args[1]["sync_type"] == "collection"  # sync_type should be "collection"


@pytest.mark.asyncio
async def test_sync_wantlist_only(client: AsyncClient, db_session: AsyncSession):
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

    # Mock the celery task
    with patch("src.api.v1.endpoints.collections.sync_collection_task") as mock_task:
        mock_task.delay = MagicMock()

        # Sync want list only
        response = await client.post(
            "/api/v1/collections/sync/wantlist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Want list sync queued successfully"

        # Verify task was called with correct arguments
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args
        assert call_args[0][0] == str(user.id)
        assert call_args[1]["sync_type"] == "wantlist"  # sync_type should be "wantlist"


@pytest.mark.asyncio
async def test_sync_requires_auth(client: AsyncClient):
    # Test that sync endpoints require authentication
    response = await client.post("/api/v1/collections/sync")
    assert response.status_code == 401

    response = await client.post("/api/v1/collections/sync/collection")
    assert response.status_code == 401

    response = await client.post("/api/v1/collections/sync/wantlist")
    assert response.status_code == 401
