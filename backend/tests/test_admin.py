import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_config import AppConfig, OAuthProvider


@pytest.mark.asyncio
async def test_admin_get_app_configs_not_admin(client: AsyncClient):
    """Test accessing admin endpoint as non-admin user."""
    # Register and login as regular user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Try to access admin endpoint
    response = await client.get(
        "/api/v1/admin/app-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    data = response.json()
    assert "You don't have permission to access this resource." == data["detail"]


@pytest.mark.asyncio
async def test_admin_get_app_configs(client: AsyncClient):
    """Test getting app configurations as admin."""
    # Register and login as admin user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Get app configs
    response = await client.get(
        "/api/v1/admin/app-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_admin_create_app_config(client: AsyncClient):
    """Test creating app configuration as admin."""
    # Register and login as admin user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Create app config
    response = await client.put(
        "/api/v1/admin/app-config/discogs",
        json={
            "provider": "discogs",
            "consumer_key": "test_consumer_key",
            "consumer_secret": "test_consumer_secret",
            "callback_url": "http://localhost:3000/oauth/callback/discogs",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "discogs"
    assert data["consumer_key"].startswith("test_consu")
    assert data["consumer_key"].endswith("...")
    assert "consumer_secret" not in data  # Should not be returned
    assert data["is_configured"] is True


@pytest.mark.asyncio
async def test_admin_update_app_config(client: AsyncClient, db_session: AsyncSession):
    """Test updating app configuration as admin."""
    # Add initial config
    app_config = AppConfig(
        provider=OAuthProvider.DISCOGS,
        consumer_key="old_key",
        consumer_secret="old_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login as admin user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Update app config
    response = await client.put(
        "/api/v1/admin/app-config/discogs",
        json={
            "provider": "discogs",
            "consumer_key": "new_consumer_key",
            "consumer_secret": "new_consumer_secret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["consumer_key"].startswith("new_consum")
    assert data["consumer_key"].endswith("...")


@pytest.mark.asyncio
async def test_admin_delete_app_config(client: AsyncClient, db_session: AsyncSession):
    """Test deleting app configuration as admin."""
    # Add config to delete
    app_config = AppConfig(
        provider=OAuthProvider.DISCOGS,
        consumer_key="test_key",
        consumer_secret="test_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login as admin user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Delete app config
    response = await client.delete(
        "/api/v1/admin/app-config/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Configuration for discogs deleted successfully."

    # Verify it's deleted
    response = await client.get(
        "/api/v1/admin/app-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    configs = response.json()
    assert not any(c["provider"] == "DISCOGS" for c in configs)


@pytest.mark.asyncio
async def test_admin_delete_nonexistent_config(client: AsyncClient):
    """Test deleting non-existent app configuration."""
    # Register and login as admin user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin@vinyldigger.com",
            "password": "adminpassword123",
        },
    )
    token = login_response.json()["access_token"]

    # Try to delete non-existent config
    response = await client.delete(
        "/api/v1/admin/app-config/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Configuration for discogs not found."
