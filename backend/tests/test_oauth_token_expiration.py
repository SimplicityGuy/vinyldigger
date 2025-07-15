"""Tests for OAuth token expiration and refresh handling."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import HTTPStatusError, Request, Response
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.oauth_token import OAuthProvider, OAuthToken
from src.models.user import User
from src.services.ebay import EbayService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for OAuth tests."""
    user = User(email="oauth_test@example.com", hashed_password=pwd_context.hash("testpassword123"), is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_ebay_oauth_token_expiration_detection(db_session: AsyncSession, test_user: User):
    """Test that expired eBay OAuth tokens are detected."""
    # Create an expired OAuth token
    expired_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="expired_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
    )
    db_session.add(expired_token)
    await db_session.commit()

    async with EbayService() as service:
        # Mock the HTTP client to simulate 401 Unauthorized
        mock_response = Response(
            status_code=401, json={"error": "invalid_token"}, request=Request("GET", "https://api.ebay.com/test")
        )

        with patch.object(
            service.client,
            "get",
            side_effect=HTTPStatusError("Unauthorized", request=mock_response.request, response=mock_response),
        ):
            # Attempt to search with expired token
            results = await service.search(query="test", filters={}, db=db_session, user_id=test_user.id)

            # Should return empty results when token is expired
            assert results == []


@pytest.mark.asyncio
async def test_ebay_oauth_token_refresh(db_session: AsyncSession, test_user: User):
    """Test that expired OAuth tokens return empty results (refresh not implemented yet)."""
    # Create an expired OAuth token with refresh token
    expired_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="expired_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(expired_token)
    await db_session.commit()

    async with EbayService() as service:
        # Mock 401 response for expired token
        mock_response = Response(
            status_code=401, json={"error": "invalid_token"}, request=Request("GET", "https://api.ebay.com/test")
        )

        with patch.object(
            service.client,
            "get",
            side_effect=HTTPStatusError("Unauthorized", request=mock_response.request, response=mock_response),
        ):
            results = await service.search(query="test", filters={}, db=db_session, user_id=test_user.id)

            # Should return empty results when token is expired (TODO: implement refresh)
            assert results == []


@pytest.mark.asyncio
async def test_ebay_oauth_refresh_failure(db_session: AsyncSession, test_user: User):
    """Test handling when OAuth token is invalid and no refresh is available."""
    # Create an expired OAuth token
    expired_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="expired_access_token",
        refresh_token="invalid_refresh_token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(expired_token)
    await db_session.commit()

    async with EbayService() as service:
        # Mock 401 response indicating invalid token
        mock_response = Response(
            status_code=401,
            json={"error": "invalid_grant"},
            request=Request("GET", "https://api.ebay.com/buy/browse/v1/item_summary/search"),
        )

        with patch.object(
            service.client,
            "get",
            side_effect=HTTPStatusError("Unauthorized", request=mock_response.request, response=mock_response),
        ):
            results = await service.search(query="test", filters={}, db=db_session, user_id=test_user.id)

            # Should return empty results when token is invalid
            assert results == []

            # Verify the token still exists (no auto-deletion implemented)
            result = await db_session.execute(
                select(OAuthToken).where(OAuthToken.user_id == test_user.id, OAuthToken.provider == OAuthProvider.EBAY)
            )
            token = result.scalar_one_or_none()
            # Token should still exist but be expired
            assert token is not None
            assert token.expires_at is not None and token.expires_at < datetime.now(UTC)


@pytest.mark.asyncio
async def test_discogs_oauth_session_validity_check(db_session: AsyncSession, test_user: User):
    """Test Discogs OAuth token storage and retrieval."""
    # Discogs uses OAuth 1.0a which doesn't have expiration, but tokens can be revoked
    from src.models.app_config import AppConfig

    # Create app config for Discogs
    app_config = AppConfig(
        provider=OAuthProvider.DISCOGS,
        consumer_key="test_key",
        consumer_secret="test_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    # Create a valid OAuth token
    oauth_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="valid_token",
        access_token_secret="valid_secret",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Verify token is stored correctly
    result = await db_session.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == test_user.id,
            OAuthToken.provider == OAuthProvider.DISCOGS,
        )
    )
    stored_token = result.scalar_one_or_none()

    assert stored_token is not None
    assert stored_token.access_token == "valid_token"
    assert stored_token.access_token_secret == "valid_secret"
    assert stored_token.expires_at is None  # OAuth 1.0a tokens don't expire


@pytest.mark.asyncio
async def test_oauth_token_cleanup_on_logout(db_session: AsyncSession, test_user: User):
    """Test that OAuth tokens are cleaned up on user logout."""
    # Create OAuth tokens for both providers
    discogs_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="discogs_token",
        access_token_secret="discogs_secret",
    )
    ebay_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="ebay_token",
        refresh_token="ebay_refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    db_session.add_all([discogs_token, ebay_token])
    await db_session.commit()

    # Simulate logout by revoking tokens
    from src.api.v1.endpoints.oauth import revoke_oauth_access as revoke_oauth

    # Revoke Discogs token
    await revoke_oauth(provider=OAuthProvider.DISCOGS, current_user=test_user, db=db_session)

    # Revoke eBay token
    await revoke_oauth(provider=OAuthProvider.EBAY, current_user=test_user, db=db_session)

    # Verify tokens are deleted
    result = await db_session.execute(select(OAuthToken).where(OAuthToken.user_id == test_user.id))
    tokens = result.scalars().all()
    assert len(tokens) == 0


@pytest.mark.asyncio
async def test_concurrent_token_access(db_session: AsyncSession, test_user: User):
    """Test that concurrent token access is handled properly."""
    # Create a valid OAuth token
    valid_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(UTC) + timedelta(hours=2),  # Still valid
    )
    db_session.add(valid_token)
    await db_session.commit()

    async with EbayService() as service:
        # Simulate concurrent requests
        import asyncio

        async def make_request():
            return await service.get_oauth_token(db_session, test_user.id)

        # Run multiple concurrent requests
        results = await asyncio.gather(make_request(), make_request(), make_request())

        # All requests should get the same token
        assert all(token == "valid_access_token" for token in results)
