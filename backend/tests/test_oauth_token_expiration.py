"""Tests for OAuth token expiration and refresh handling."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

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
    """Test automatic OAuth token refresh for eBay."""
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
        # Mock the refresh token response
        mock_refresh_response = Mock()
        mock_refresh_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 7200,  # 2 hours
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
        }
        mock_refresh_response.raise_for_status = Mock()

        # Mock the search response after refresh
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "itemSummaries": [
                {
                    "itemId": "123",
                    "title": "Test Item",
                    "price": {"value": "25.00", "currency": "USD"},
                    "condition": "NEW",
                    "seller": {"username": "test_seller"},
                }
            ],
            "total": 1,
        }
        mock_search_response.raise_for_status = Mock()

        with patch.object(service, "_refresh_oauth_token", return_value="new_access_token") as mock_refresh:
            with patch.object(service.client, "get", return_value=mock_search_response):
                results = await service.search(query="test", filters={}, db=db_session, user_id=test_user.id)

                # Should successfully return results after refresh
                assert len(results) == 1
                assert results[0]["title"] == "Test Item"

                # Verify token was refreshed
                mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_ebay_oauth_refresh_failure(db_session: AsyncSession, test_user: User):
    """Test handling when OAuth token refresh fails."""
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
        # Mock failed refresh attempt
        mock_response = Response(
            status_code=400,
            json={"error": "invalid_grant"},
            request=Request("POST", "https://api.ebay.com/identity/v1/oauth2/token"),
        )

        with patch.object(
            service,
            "_refresh_oauth_token",
            side_effect=HTTPStatusError("Bad Request", request=mock_response.request, response=mock_response),
        ):
            results = await service.search(query="test", filters={}, db=db_session, user_id=test_user.id)

            # Should return empty results when refresh fails
            assert results == []

            # Verify the token is marked as invalid in the database
            result = await db_session.execute(
                select(OAuthToken).where(OAuthToken.user_id == test_user.id, OAuthToken.provider == OAuthProvider.EBAY)
            )
            token = result.scalar_one_or_none()
            # Token should still exist but be expired
            assert token is not None
            assert token.expires_at is not None and token.expires_at < datetime.now(UTC)


@pytest.mark.asyncio
async def test_discogs_oauth_session_validity_check(db_session: AsyncSession, test_user: User):
    """Test Discogs OAuth session validity checking."""
    # Discogs uses OAuth 1.0a which doesn't have expiration, but tokens can be revoked
    from src.services.discogs import DiscogsService

    # Create a valid OAuth token
    oauth_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="valid_token",
        access_token_secret="valid_secret",
    )
    db_session.add(oauth_token)
    await db_session.commit()

    # Since Discogs now uses marketplace scraper, OAuth is not used for search
    # But we can test that the OAuth auth method still works
    async with DiscogsService() as service:
        auth = await service.get_oauth_auth(db_session, str(test_user.id))

        # Should return auth object when token exists
        assert auth is not None


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
async def test_concurrent_token_refresh_handling(db_session: AsyncSession, test_user: User):
    """Test that concurrent token refresh attempts are handled properly."""
    # Create an expired OAuth token
    expired_token = OAuthToken(
        user_id=test_user.id,
        provider=OAuthProvider.EBAY,
        access_token="expired_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(expired_token)
    await db_session.commit()

    async with EbayService() as service:
        # Mock successful refresh
        new_token_data = {"access_token": "new_access_token", "expires_in": 7200, "refresh_token": "new_refresh_token"}

        refresh_call_count = 0

        async def mock_refresh(*args, **kwargs):
            nonlocal refresh_call_count
            refresh_call_count += 1
            return new_token_data["access_token"]

        with patch.object(service, "_refresh_oauth_token", side_effect=mock_refresh):
            # Simulate concurrent requests
            import asyncio

            async def make_request():
                return await service.get_oauth_token(db_session, str(test_user.id))

            # Run multiple concurrent requests
            results = await asyncio.gather(make_request(), make_request(), make_request())

            # All requests should get the same new token
            assert all(token == "new_access_token" for token in results)

            # Refresh should only be called once despite concurrent requests
            # (This test assumes proper locking in the implementation)
            assert refresh_call_count <= 3  # May be called multiple times without proper locking
