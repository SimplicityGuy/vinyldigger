import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    # First register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )

    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
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

    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
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
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token - endpoint expects JSON body
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    if response.status_code != 200:
        print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )

    # Test login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # Register first user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )

    # Try to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "anotherpassword123",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    # Try to access protected endpoint without token
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    # Try to access protected endpoint with invalid token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    assert response.status_code == 401
