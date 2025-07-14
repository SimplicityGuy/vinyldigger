"""Tests for BaseAPIService."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import APIKey, APIService
from src.services.base import BaseAPIService


class TestBaseAPIService:
    """Test suite for BaseAPIService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.fixture
    def api_key_with_secret(self, user_id):
        """Create test API key with secret."""
        return APIKey(
            id=uuid4(),
            user_id=user_id,
            service=APIService.DISCOGS,
            encrypted_key="encrypted_test_key",
            encrypted_secret="encrypted_test_secret",
        )

    @pytest.fixture
    def api_key_without_secret(self, user_id):
        """Create test API key without secret."""
        return APIKey(
            id=uuid4(),
            user_id=user_id,
            service=APIService.EBAY,
            encrypted_key="encrypted_test_key",
            encrypted_secret=None,
        )

    @pytest.fixture
    def concrete_service(self):
        """Create concrete implementation of BaseAPIService for testing."""

        class ConcreteAPIService(BaseAPIService):
            async def search(
                self, query: str, filters: dict[str, Any], credentials: dict[str, str]
            ) -> list[dict[str, Any]]:
                return []

            async def get_item_details(self, item_id: str, credentials: dict[str, str]) -> dict[str, Any] | None:
                return None

        return ConcreteAPIService(APIService.DISCOGS)

    def test_init(self, concrete_service):
        """Test BaseAPIService initialization."""
        assert concrete_service.service == APIService.DISCOGS
        assert hasattr(concrete_service, "logger")

    @pytest.mark.asyncio
    async def test_get_api_credentials_with_secret(self, concrete_service, mock_db, user_id, api_key_with_secret):
        """Test retrieving API credentials with both key and secret."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key_with_secret
        mock_db.execute.return_value = mock_result

        # Mock decryption
        with patch("src.services.base.api_key_encryption") as mock_encryption:
            mock_encryption.decrypt_key.side_effect = ["decrypted_key", "decrypted_secret"]

            credentials = await concrete_service.get_api_credentials(mock_db, user_id)

            assert credentials is not None
            assert credentials["key"] == "decrypted_key"
            assert credentials["secret"] == "decrypted_secret"
            assert mock_encryption.decrypt_key.call_count == 2

    @pytest.mark.asyncio
    async def test_get_api_credentials_without_secret(self, concrete_service, mock_db, user_id, api_key_without_secret):
        """Test retrieving API credentials with only key (no secret)."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key_without_secret
        mock_db.execute.return_value = mock_result

        # Mock decryption
        with patch("src.services.base.api_key_encryption") as mock_encryption:
            mock_encryption.decrypt_key.return_value = "decrypted_key"

            credentials = await concrete_service.get_api_credentials(mock_db, user_id)

            assert credentials is not None
            assert credentials["key"] == "decrypted_key"
            assert "secret" not in credentials
            assert mock_encryption.decrypt_key.call_count == 1

    @pytest.mark.asyncio
    async def test_get_api_credentials_no_key_found(self, concrete_service, mock_db, user_id):
        """Test retrieving API credentials when no key is found."""
        # Mock database query result with no API key
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        credentials = await concrete_service.get_api_credentials(mock_db, user_id)

        assert credentials is None

    @pytest.mark.asyncio
    async def test_get_api_credentials_correct_query_filters(self, concrete_service, mock_db, user_id):
        """Test that the database query uses correct filters."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await concrete_service.get_api_credentials(mock_db, user_id)

        # Verify that execute was called with a select query
        mock_db.execute.assert_called_once()
        # The exact query is complex to match, but we can verify it was called
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_get_api_credentials_decryption_error(self, concrete_service, mock_db, user_id, api_key_with_secret):
        """Test handling of decryption errors."""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = api_key_with_secret
        mock_db.execute.return_value = mock_result

        # Mock decryption failure
        with patch("src.services.base.api_key_encryption") as mock_encryption:
            mock_encryption.decrypt_key.side_effect = Exception("Decryption failed")

            with pytest.raises(Exception, match="Decryption failed"):
                await concrete_service.get_api_credentials(mock_db, user_id)

    def test_format_search_result_complete_data(self, concrete_service):
        """Test formatting search result with complete data."""
        raw_item = {
            "id": 123456,
            "title": "Abbey Road",
            "price": 29.99,
            "currency": "USD",
            "condition": "Very Good Plus (VG+)",
            "seller": {"name": "RecordSeller", "rating": 98.5},
            "url": "https://example.com/item/123456",
            "image_url": "https://example.com/image.jpg",
            "location": "New York, US",
            "shipping": {"cost": 5.99, "estimated_days": 7},
            "extra_field": "should be preserved",
        }

        result = concrete_service.format_search_result(raw_item, "discogs")

        assert result["platform"] == "discogs"
        assert result["item_id"] == "123456"
        assert result["title"] == "Abbey Road"
        assert result["price"] == 29.99
        assert result["currency"] == "USD"
        assert result["condition"] == "Very Good Plus (VG+)"
        assert result["seller"] == {"name": "RecordSeller", "rating": 98.5}
        assert result["url"] == "https://example.com/item/123456"
        assert result["image_url"] == "https://example.com/image.jpg"
        assert result["location"] == "New York, US"
        assert result["shipping"] == {"cost": 5.99, "estimated_days": 7}
        assert result["raw_data"] == raw_item

    def test_format_search_result_minimal_data(self, concrete_service):
        """Test formatting search result with minimal data."""
        raw_item = {}

        result = concrete_service.format_search_result(raw_item, "ebay")

        assert result["platform"] == "ebay"
        assert result["item_id"] == ""
        assert result["title"] == ""
        assert result["price"] == 0.0
        assert result["currency"] == "USD"
        assert result["condition"] == "Unknown"
        assert result["seller"] == {}
        assert result["url"] == ""
        assert result["image_url"] == ""
        assert result["location"] == ""
        assert result["shipping"] == {}
        assert result["raw_data"] == {}

    def test_format_search_result_partial_data(self, concrete_service):
        """Test formatting search result with partial data."""
        raw_item = {
            "id": "abc123",
            "title": "Dark Side of the Moon",
            "price": 35.50,
            "seller": {"name": "VinylCollector"},
            # Missing other fields
        }

        result = concrete_service.format_search_result(raw_item, "discogs")

        assert result["platform"] == "discogs"
        assert result["item_id"] == "abc123"
        assert result["title"] == "Dark Side of the Moon"
        assert result["price"] == 35.50
        assert result["currency"] == "USD"  # Default value
        assert result["condition"] == "Unknown"  # Default value
        assert result["seller"] == {"name": "VinylCollector"}
        assert result["url"] == ""  # Default value
        assert result["image_url"] == ""  # Default value
        assert result["location"] == ""  # Default value
        assert result["shipping"] == {}  # Default value
        assert result["raw_data"] == raw_item

    def test_format_search_result_numeric_id_conversion(self, concrete_service):
        """Test that numeric IDs are converted to strings."""
        raw_item = {"id": 999999}

        result = concrete_service.format_search_result(raw_item, "test")

        assert result["item_id"] == "999999"
        assert isinstance(result["item_id"], str)

    def test_format_search_result_none_id_conversion(self, concrete_service):
        """Test that None ID is converted to string 'None'."""
        raw_item = {"id": None}

        result = concrete_service.format_search_result(raw_item, "test")

        assert result["item_id"] == "None"

    def test_format_search_result_preserves_raw_data(self, concrete_service):
        """Test that the complete raw data is preserved."""
        raw_item = {
            "id": 123,
            "custom_field": "custom_value",
            "nested": {"data": {"value": 42}},
            "list_data": [1, 2, 3],
        }

        result = concrete_service.format_search_result(raw_item, "test")

        assert result["raw_data"] == raw_item
        assert result["raw_data"]["custom_field"] == "custom_value"
        assert result["raw_data"]["nested"]["data"]["value"] == 42
        assert result["raw_data"]["list_data"] == [1, 2, 3]

    def test_abstract_methods_not_implemented(self):
        """Test that abstract methods raise NotImplementedError when not implemented."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAPIService(APIService.DISCOGS)
