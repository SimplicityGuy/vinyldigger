from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.app_config import AppConfig, OAuthProvider
from src.models.oauth_token import OAuthToken


@pytest.mark.asyncio
async def test_oauth_status_not_configured(client: AsyncClient):
    """Test OAuth status when provider is not configured."""
    # Register and login
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

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is False
    assert data["is_authorized"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_oauth_status_configured_not_authorized(client: AsyncClient, db_session: AsyncSession):
    """Test OAuth status when provider is configured but user not authorized."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.DISCOGS,
        consumer_key="test_consumer_key",
        consumer_secret="encrypted_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login
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

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["is_authorized"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_oauth_status_fully_authorized(client: AsyncClient, db_session: AsyncSession):
    """Test OAuth status when provider is configured and user is authorized."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.DISCOGS,
        consumer_key="test_consumer_key",
        consumer_secret="encrypted_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login
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

    # Get user ID
    user_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = user_response.json()["id"]

    # Add OAuth token for user
    oauth_token = OAuthToken(
        user_id=UUID(user_id),
        provider=OAuthProvider.DISCOGS,
        access_token="encrypted_token",
        access_token_secret="encrypted_secret",
        provider_username="testdiscogs",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["is_authorized"] is True
    assert data["username"] == "testdiscogs"


@pytest.mark.asyncio
async def test_oauth_authorize_no_config(client: AsyncClient):
    """Test initiating OAuth when provider is not configured."""
    # Register and login
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

    # Try to initiate OAuth
    response = await client.post(
        "/api/v1/oauth/authorize/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    data = response.json()
    assert "not configured" in data["detail"]


@pytest.mark.asyncio
async def test_oauth_revoke(client: AsyncClient, db_session: AsyncSession):
    """Test revoking OAuth access."""
    # Register and login
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

    # Get user ID
    user_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = user_response.json()["id"]

    # Add OAuth token for user
    oauth_token = OAuthToken(
        user_id=UUID(user_id),
        provider=OAuthProvider.DISCOGS,
        access_token="encrypted_token",
        access_token_secret="encrypted_secret",
        provider_username="testdiscogs",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Revoke OAuth
    response = await client.delete(
        "/api/v1/oauth/revoke/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully revoked DISCOGS access."

    # Verify token is deleted
    response = await client.get(
        "/api/v1/oauth/status/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["is_authorized"] is False


@pytest.mark.asyncio
async def test_oauth_revoke_not_authorized(client: AsyncClient):
    """Test revoking OAuth when not authorized."""
    # Register and login
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

    # Try to revoke OAuth
    response = await client.delete(
        "/api/v1/oauth/revoke/discogs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "No authorization found" in data["detail"]


@pytest.mark.asyncio
async def test_ebay_oauth_status_not_configured(client: AsyncClient):
    """Test eBay OAuth status when provider is not configured."""
    # Register and login
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

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is False
    assert data["is_authorized"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_ebay_oauth_status_configured_not_authorized(client: AsyncClient, db_session: AsyncSession):
    """Test eBay OAuth status when provider is configured but user not authorized."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_ebay_client_id",
        consumer_secret="encrypted_ebay_secret",
        redirect_uri="http://localhost:3000/oauth/callback/ebay",
        scope="https://api.ebay.com/oauth/api_scope",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login
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

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["is_authorized"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_ebay_oauth_status_fully_authorized(client: AsyncClient, db_session: AsyncSession):
    """Test eBay OAuth status when provider is configured and user is authorized."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_ebay_client_id",
        consumer_secret="encrypted_ebay_secret",
        redirect_uri="http://localhost:3000/oauth/callback/ebay",
        scope="https://api.ebay.com/oauth/api_scope",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login
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

    # Get user ID
    user_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = user_response.json()["id"]

    # Add OAuth token for user
    oauth_token = OAuthToken(
        user_id=UUID(user_id),
        provider=OAuthProvider.EBAY,
        access_token="encrypted_ebay_token",
        refresh_token="encrypted_ebay_refresh",
        provider_username="testebay",
        provider_user_id="ebay123",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Check OAuth status
    response = await client.get(
        "/api/v1/oauth/status/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_configured"] is True
    assert data["is_authorized"] is True
    assert data["username"] == "testebay"


@pytest.mark.asyncio
async def test_ebay_oauth_authorize_returns_url(client: AsyncClient, db_session: AsyncSession):
    """Test initiating eBay OAuth returns authorization URL."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_ebay_client_id",
        consumer_secret="encrypted_ebay_secret",
        redirect_uri="http://localhost:3000/oauth/callback/ebay",
        scope="https://api.ebay.com/oauth/api_scope",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Register and login
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

    # Initiate OAuth
    response = await client.post(
        "/api/v1/oauth/authorize/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "https://auth.ebay.com/oauth2/authorize" in data["authorization_url"]
    assert "state" in data
    assert len(data["state"]) > 0


@pytest.mark.asyncio
async def test_ebay_oauth_revoke(client: AsyncClient, db_session: AsyncSession):
    """Test revoking eBay OAuth access."""
    # Register and login
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

    # Get user ID
    user_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = user_response.json()["id"]

    # Add OAuth token for user
    oauth_token = OAuthToken(
        user_id=UUID(user_id),
        provider=OAuthProvider.EBAY,
        access_token="encrypted_ebay_token",
        refresh_token="encrypted_ebay_refresh",
        provider_username="testebay",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Revoke OAuth
    response = await client.delete(
        "/api/v1/oauth/revoke/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully revoked EBAY access."

    # Verify token is deleted
    response = await client.get(
        "/api/v1/oauth/status/ebay",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["is_authorized"] is False
