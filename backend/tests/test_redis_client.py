"""Tests for Redis client functionality."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from src.core.redis_client import OAuthTokenStore, close_redis, get_redis


class TestRedisClient:
    """Test suite for Redis client functions."""

    @pytest.fixture(autouse=True)
    def reset_redis_client(self):
        """Reset global Redis client before each test."""
        import src.core.redis_client

        src.core.redis_client._redis_client = None

    @pytest.mark.asyncio
    async def test_get_redis_creates_client(self):
        """Test that get_redis creates a Redis client."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            client = await get_redis()

            assert client == mock_client
            mock_from_url.assert_called_once()
            call_args = mock_from_url.call_args
            assert call_args[1]["encoding"] == "utf-8"
            assert call_args[1]["decode_responses"] is True

    @pytest.mark.asyncio
    async def test_get_redis_singleton_pattern(self):
        """Test that get_redis returns the same instance on subsequent calls."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            client1 = await get_redis()
            client2 = await get_redis()

            assert client1 is client2
            # from_url should only be called once
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_uses_settings_url(self):
        """Test that get_redis uses the Redis URL from settings."""
        with (
            patch("src.core.redis_client.redis.from_url") as mock_from_url,
            patch("src.core.redis_client.settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://test:6379/1"
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            await get_redis()

            mock_from_url.assert_called_once_with(
                "redis://test:6379/1",
                encoding="utf-8",
                decode_responses=True,
            )

    @pytest.mark.asyncio
    async def test_close_redis_with_client(self):
        """Test closing Redis connection when client exists."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            # First get a client
            await get_redis()

            # Then close it
            await close_redis()

            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis_without_client(self):
        """Test closing Redis connection when no client exists."""
        # This should not raise any exceptions
        await close_redis()

    @pytest.mark.asyncio
    async def test_close_redis_resets_client(self):
        """Test that close_redis resets the global client variable."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            # Get a client, then close it
            await get_redis()
            await close_redis()

            # Getting a new client should create a new instance
            await get_redis()

            # from_url should be called twice (once before close, once after)
            assert mock_from_url.call_count == 2


class TestOAuthTokenStore:
    """Test suite for OAuthTokenStore class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock(spec=Redis)
        # Set up async methods to return values properly
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def token_store(self, mock_redis):
        """Create OAuthTokenStore instance with mock Redis."""
        return OAuthTokenStore(mock_redis)

    @pytest.fixture
    def sample_token_data(self):
        """Create sample OAuth token data."""
        return {
            "user_id": str(uuid4()),
            "request_token": "oauth_token_123",
            "request_token_secret": "oauth_secret_456",
            "provider": "discogs",
        }

    def test_init(self, mock_redis):
        """Test OAuthTokenStore initialization."""
        store = OAuthTokenStore(mock_redis)
        assert store.redis == mock_redis
        assert store.PREFIX == "oauth:request:"
        assert store.TTL == 600

    @pytest.mark.asyncio
    async def test_store_request_token(self, token_store, mock_redis, sample_token_data):
        """Test storing OAuth request token."""
        state = "test_state_123"

        await token_store.store_request_token(
            state=state,
            user_id=sample_token_data["user_id"],
            request_token=sample_token_data["request_token"],
            request_token_secret=sample_token_data["request_token_secret"],
            provider=sample_token_data["provider"],
        )

        expected_key = f"oauth:request:{state}"
        expected_data = json.dumps(sample_token_data)

        mock_redis.setex.assert_called_once_with(
            expected_key,
            600,  # TTL
            expected_data,
        )

    @pytest.mark.asyncio
    async def test_store_request_token_logging(self, token_store, mock_redis):
        """Test that storing request token generates appropriate logs."""
        with patch("src.core.redis_client.logger") as mock_logger:
            state = "test_state_123"

            await token_store.store_request_token(
                state=state,
                user_id="test_user",
                request_token="token",
                request_token_secret="secret",
                provider="test",
            )

            mock_logger.debug.assert_called_once_with(f"Stored OAuth request token for state: {state}")

    @pytest.mark.asyncio
    async def test_get_request_token_success(self, token_store, mock_redis, sample_token_data):
        """Test successfully retrieving OAuth request token."""
        state = "test_state_123"
        stored_data = json.dumps(sample_token_data)

        mock_redis.get.return_value = stored_data

        result = await token_store.get_request_token(state)

        expected_key = f"oauth:request:{state}"
        mock_redis.get.assert_called_once_with(expected_key)
        assert result == sample_token_data

    @pytest.mark.asyncio
    async def test_get_request_token_not_found(self, token_store, mock_redis):
        """Test retrieving OAuth request token when not found."""
        state = "nonexistent_state"
        mock_redis.get.return_value = None

        with patch("src.core.redis_client.logger") as mock_logger:
            result = await token_store.get_request_token(state)

            assert result is None
            mock_logger.warning.assert_called_once_with(f"No OAuth request token found for state: {state}")

    @pytest.mark.asyncio
    async def test_get_request_token_invalid_json(self, token_store, mock_redis):
        """Test retrieving OAuth request token with invalid JSON data."""
        state = "test_state_123"
        mock_redis.get.return_value = "invalid json data"

        # This should raise a JSONDecodeError since the code doesn't catch it
        with pytest.raises(json.JSONDecodeError):
            await token_store.get_request_token(state)

    @pytest.mark.asyncio
    async def test_get_request_token_invalid_format(self, token_store, mock_redis):
        """Test retrieving OAuth request token with wrong data format."""
        state = "test_state_123"
        # Valid JSON but not a dict
        mock_redis.get.return_value = json.dumps(["not", "a", "dict"])

        with patch("src.core.redis_client.logger") as mock_logger:
            result = await token_store.get_request_token(state)

            assert result is None
            mock_logger.error.assert_called_once_with(f"Invalid OAuth token data format for state: {state}")

    @pytest.mark.asyncio
    async def test_get_request_token_success_logging(self, token_store, mock_redis, sample_token_data):
        """Test that successful token retrieval generates appropriate logs."""
        state = "test_state_123"
        stored_data = json.dumps(sample_token_data)
        mock_redis.get.return_value = stored_data

        with patch("src.core.redis_client.logger") as mock_logger:
            await token_store.get_request_token(state)

            mock_logger.debug.assert_called_once_with(f"Retrieved OAuth request token for state: {state}")

    @pytest.mark.asyncio
    async def test_delete_request_token(self, token_store, mock_redis):
        """Test deleting OAuth request token."""
        state = "test_state_123"

        await token_store.delete_request_token(state)

        expected_key = f"oauth:request:{state}"
        mock_redis.delete.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_delete_request_token_logging(self, token_store, mock_redis):
        """Test that deleting request token generates appropriate logs."""
        with patch("src.core.redis_client.logger") as mock_logger:
            state = "test_state_123"

            await token_store.delete_request_token(state)

            mock_logger.debug.assert_called_once_with(f"Deleted OAuth request token for state: {state}")

    @pytest.mark.asyncio
    async def test_store_and_retrieve_workflow(self, token_store, mock_redis, sample_token_data):
        """Test complete store and retrieve workflow."""
        state = "workflow_test_state"

        # Configure mock to return stored data when get is called
        def mock_get(key):
            if key == f"oauth:request:{state}":
                return json.dumps(sample_token_data)
            return None

        mock_redis.get.side_effect = mock_get

        # Store token
        await token_store.store_request_token(
            state=state,
            user_id=sample_token_data["user_id"],
            request_token=sample_token_data["request_token"],
            request_token_secret=sample_token_data["request_token_secret"],
            provider=sample_token_data["provider"],
        )

        # Retrieve token
        result = await token_store.get_request_token(state)

        assert result == sample_token_data

    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self, mock_redis):
        """Test handling of Redis connection errors."""
        mock_redis.setex.side_effect = Exception("Redis connection failed")
        token_store = OAuthTokenStore(mock_redis)

        with pytest.raises(Exception, match="Redis connection failed"):
            await token_store.store_request_token(
                state="test",
                user_id="user",
                request_token="token",
                request_token_secret="secret",
                provider="test",
            )

    @pytest.mark.asyncio
    async def test_key_prefix_consistency(self, token_store):
        """Test that all methods use consistent key prefixes."""
        state = "test_state"
        expected_key = f"oauth:request:{state}"

        # Mock Redis to capture the keys used
        mock_redis = token_store.redis

        # Set up mock to return None for get calls to avoid JSON parsing issues
        mock_redis.get.return_value = None

        # Test store method
        await token_store.store_request_token("test_state", "user", "token", "secret", "provider")
        store_key = mock_redis.setex.call_args[0][0]
        assert store_key == expected_key

        # Test get method
        await token_store.get_request_token(state)
        get_key = mock_redis.get.call_args[0][0]
        assert get_key == expected_key

        # Test delete method
        await token_store.delete_request_token(state)
        delete_key = mock_redis.delete.call_args[0][0]
        assert delete_key == expected_key

    @pytest.mark.asyncio
    async def test_json_serialization_edge_cases(self, token_store, mock_redis):
        """Test JSON serialization with edge cases."""
        state = "edge_case_state"

        # Test with special characters
        special_data = {
            "user_id": "user_with_special_chars_àáâã",
            "request_token": "token_with_symbols_!@#$%",
            "request_token_secret": "secret_with_unicode_🔐",
            "provider": "provider_with_spaces and more",
        }

        await token_store.store_request_token(
            state=state,
            user_id=special_data["user_id"],
            request_token=special_data["request_token"],
            request_token_secret=special_data["request_token_secret"],
            provider=special_data["provider"],
        )

        # Verify the data was JSON serialized correctly
        stored_json = mock_redis.setex.call_args[0][2]
        parsed_data = json.loads(stored_json)
        assert parsed_data == special_data

    def test_constants(self):
        """Test that class constants have expected values."""
        assert OAuthTokenStore.PREFIX == "oauth:request:"
        assert OAuthTokenStore.TTL == 600  # 10 minutes
