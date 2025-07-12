from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AppConfig, OAuthProvider, OAuthToken
from src.services.ebay import EbayService


@pytest.mark.asyncio
async def test_ebay_get_oauth_token(db_session: AsyncSession):
    """Test getting user's OAuth token."""
    user_id = uuid4()
    token = OAuthToken(
        user_id=user_id,
        provider=OAuthProvider.EBAY,
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        provider_username="testuser",
    )
    db_session.add(token)
    await db_session.commit()

    async with EbayService() as service:
        result = await service.get_oauth_token(db_session, user_id)
        assert result == "test_access_token"


@pytest.mark.asyncio
async def test_ebay_get_oauth_token_not_found(db_session: AsyncSession):
    """Test getting OAuth token when not found."""
    user_id = uuid4()

    async with EbayService() as service:
        result = await service.get_oauth_token(db_session, user_id)
        assert result is None


@pytest.mark.asyncio
async def test_ebay_get_app_access_token(db_session: AsyncSession):
    """Test getting application access token."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_client_id",
        consumer_secret="test_client_secret",
        scope="https://api.ebay.com/oauth/api_scope",
    )
    db_session.add(app_config)
    await db_session.commit()

    async with EbayService() as service:
        with patch.object(service.client, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "app_token_123"}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = await service._get_app_access_token(db_session)
            assert result == "app_token_123"

            # Verify the request
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/identity/v1/oauth2/token"
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["data"]["grant_type"] == "client_credentials"


@pytest.mark.asyncio
async def test_ebay_search_with_oauth_token(db_session: AsyncSession):
    """Test searching eBay with user OAuth token."""
    user_id = uuid4()

    # Add OAuth token
    token = OAuthToken(
        user_id=user_id,
        provider=OAuthProvider.EBAY,
        access_token="user_oauth_token",
        refresh_token="refresh_token",
        provider_username="testuser",
    )
    db_session.add(token)
    await db_session.commit()

    async with EbayService() as service:
        with patch.object(service.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "itemSummaries": [
                    {
                        "itemId": "123",
                        "title": "Test Record",
                        "price": {"value": "10.00", "currency": "USD"},
                        "condition": "Good",
                        "seller": {"username": "seller1"},
                        "itemLocation": {"country": "US"},
                        "itemWebUrl": "https://ebay.com/item/123",
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            results = await service.search("test vinyl", {}, db_session, user_id)

            assert len(results) == 1
            assert results[0]["id"] == "123"
            assert results[0]["title"] == "Test Record"
            assert results[0]["price"] == 10.0

            # Verify authorization header uses OAuth token
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer user_oauth_token"


@pytest.mark.asyncio
async def test_ebay_search_with_app_token(db_session: AsyncSession):
    """Test searching eBay with app token when no user OAuth."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_client_id",
        consumer_secret="test_client_secret",
        scope="https://api.ebay.com/oauth/api_scope",
    )
    db_session.add(app_config)
    await db_session.commit()

    async with EbayService() as service:
        with patch.object(service.client, "post") as mock_post:
            # Mock token request
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {"access_token": "app_token_123"}
            mock_token_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_token_response

            with patch.object(service.client, "get") as mock_get:
                # Mock search request
                mock_search_response = MagicMock()
                mock_search_response.json.return_value = {
                    "itemSummaries": [
                        {
                            "itemId": "456",
                            "title": "Another Record",
                            "price": {"value": "20.00", "currency": "USD"},
                            "condition": "New",
                            "seller": {"username": "seller2"},
                            "itemLocation": {"country": "UK"},
                            "itemWebUrl": "https://ebay.com/item/456",
                        }
                    ]
                }
                mock_search_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_search_response

                # Search without user_id
                results = await service.search("test vinyl", {}, db_session)

                assert len(results) == 1
                assert results[0]["id"] == "456"
                assert results[0]["title"] == "Another Record"
                assert results[0]["price"] == 20.0

                # Verify app token was used
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                assert call_args[1]["headers"]["Authorization"] == "Bearer app_token_123"


@pytest.mark.asyncio
async def test_ebay_search_with_filters(db_session: AsyncSession):
    """Test searching eBay with various filters."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_client_id",
        consumer_secret="test_client_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    async with EbayService() as service:
        # Set access token to skip auth
        service.access_token = "test_token"

        with patch.object(service.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"itemSummaries": []}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            filters = {
                "condition": ["new", "like_new"],
                "min_price": 10,
                "max_price": 100,
                "item_location": "US",
                "sort": "price_asc",
                "limit": 50,
                "offset": 0,
            }

            await service.search("vinyl records", filters, db_session)

            # Verify the request parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            params = call_args[1]["params"]

            assert params["q"] == "vinyl records"
            assert params["limit"] == 50
            assert params["offset"] == 0
            assert params["sort"] == "price"
            assert "filter" in params

            # Check filter string contains expected values
            filter_string = params["filter"]
            assert "categoryIds:{176985}" in filter_string  # Default vinyl category
            assert "conditions:{NEW,LIKE_NEW}" in filter_string
            assert "price:[10..100]" in filter_string
            assert "itemLocationCountry:US" in filter_string


@pytest.mark.asyncio
async def test_ebay_search_auth_failure(db_session: AsyncSession):
    """Test search handling auth failure."""
    async with EbayService() as service:
        service.access_token = "expired_token"

        with patch.object(service.client, "get") as mock_get:
            # Mock 401 response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
            mock_get.return_value = mock_response

            results = await service.search("test", {}, db_session)

            assert results == []
            # Verify token was cleared
            assert service.access_token is None


@pytest.mark.asyncio
async def test_ebay_get_item_details(db_session: AsyncSession):
    """Test getting item details."""
    # Add app config
    app_config = AppConfig(
        provider=OAuthProvider.EBAY,
        consumer_key="test_client_id",
        consumer_secret="test_client_secret",
    )
    db_session.add(app_config)
    await db_session.commit()

    async with EbayService() as service:
        # Set access token to skip auth
        service.access_token = "test_token"

        with patch.object(service.client, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "itemId": "789",
                "title": "Detailed Item",
                "description": "A detailed description",
                "price": {"value": "30.00", "currency": "USD"},
            }
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = await service.get_item_details("789", db_session)

            assert result is not None
            assert result["itemId"] == "789"
            assert result["title"] == "Detailed Item"

            # Verify the request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/buy/browse/v1/item/789"
            assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_ebay_format_item(db_session: AsyncSession):
    """Test formatting eBay item data."""
    async with EbayService() as service:
        item_data = {
            "itemId": "123",
            "title": "Test Vinyl Record",
            "subtitle": "Limited Edition",
            "condition": "Good",
            "conditionId": "3000",
            "price": {"value": "15.99", "currency": "USD"},
            "shippingOptions": [{"shippingCost": {"value": "5.00"}}],
            "buyingOptions": ["FIXED_PRICE", "BEST_OFFER"],
            "seller": {
                "username": "vinyl_seller",
                "feedbackPercentage": 99.5,
                "feedbackScore": 1234,
            },
            "itemLocation": {
                "city": "New York",
                "stateOrProvince": "NY",
                "country": "US",
                "postalCode": "10001",
            },
            "image": {"imageUrl": "https://example.com/image.jpg"},
            "additionalImages": [{"imageUrl": "https://example.com/image2.jpg"}],
            "itemWebUrl": "https://ebay.com/item/123",
            "categories": [{"categoryName": "Vinyl Records"}],
            "itemEndDate": "2024-12-31T23:59:59Z",
        }

        result = service._format_ebay_item(item_data)

        assert result is not None
        assert result["id"] == "123"
        assert result["title"] == "Test Vinyl Record"
        assert result["subtitle"] == "Limited Edition"
        assert result["condition"] == "Good"
        assert result["price"] == 15.99
        assert result["shipping_cost"] == 5.0
        assert result["total_price"] == pytest.approx(20.99)
        assert result["buy_it_now"] is True
        assert result["best_offer"] is True
        assert result["auction"] is False
        assert result["seller"]["username"] == "vinyl_seller"
        assert result["location"]["city"] == "New York"
        assert result["image_url"] == "https://example.com/image.jpg"
        assert len(result["additional_images"]) == 1
