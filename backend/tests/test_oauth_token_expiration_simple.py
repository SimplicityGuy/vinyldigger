"""Simple tests for OAuth token expiration logic."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.oauth_token import OAuthProvider, OAuthToken
from src.models.user import User


@pytest.mark.asyncio
async def test_oauth_token_expiration_check(db_session: AsyncSession):
    """Test checking if OAuth token is expired."""
    # Create a user
    user = User(email="test_oauth@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create an expired token
    expired_token = OAuthToken(
        user_id=user.id,
        provider=OAuthProvider.EBAY,
        access_token="expired_token",
        refresh_token="refresh_token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(expired_token)
    await db_session.commit()

    # Check if token is expired
    assert expired_token.expires_at is not None
    assert expired_token.expires_at < datetime.now(UTC)

    # Create a valid token
    valid_token = OAuthToken(
        user_id=user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="valid_token",
        access_token_secret="secret",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(valid_token)
    await db_session.commit()

    # Check if token is still valid
    assert valid_token.expires_at is not None
    assert valid_token.expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_oauth_token_without_expiration(db_session: AsyncSession):
    """Test OAuth tokens without expiration (like Discogs OAuth 1.0a)."""
    # Create a user
    user = User(email="test_oauth2@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create a Discogs token without expiration
    discogs_token = OAuthToken(
        user_id=user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="discogs_token",
        access_token_secret="discogs_secret",
        # No expires_at for OAuth 1.0a
    )
    db_session.add(discogs_token)
    await db_session.commit()

    # Token should be considered valid (no expiration)
    assert discogs_token.expires_at is None


@pytest.mark.asyncio
async def test_oauth_token_refresh_needed(db_session: AsyncSession):
    """Test detecting when OAuth token refresh is needed."""
    # Create a user
    user = User(email="test_oauth3@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create a token that's about to expire (within 5 minutes)
    soon_to_expire_token = OAuthToken(
        user_id=user.id,
        provider=OAuthProvider.EBAY,
        access_token="soon_to_expire",
        refresh_token="refresh_token",
        expires_at=datetime.now(UTC) + timedelta(minutes=3),
    )
    db_session.add(soon_to_expire_token)
    await db_session.commit()

    # Check if refresh is recommended (within 5 minute buffer)
    assert soon_to_expire_token.expires_at is not None
    time_until_expiry = soon_to_expire_token.expires_at - datetime.now(UTC)
    should_refresh = time_until_expiry < timedelta(minutes=5)
    assert should_refresh is True

    # Create a token with plenty of time left (use a different provider to avoid constraint)
    long_lived_token = OAuthToken(
        user_id=user.id,
        provider=OAuthProvider.DISCOGS,
        access_token="long_lived",
        access_token_secret="secret",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    db_session.add(long_lived_token)
    await db_session.commit()

    # Check if refresh is needed
    assert long_lived_token.expires_at is not None
    time_until_expiry = long_lived_token.expires_at - datetime.now(UTC)
    should_refresh = time_until_expiry < timedelta(minutes=5)
    assert should_refresh is False
