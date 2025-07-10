from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.discogs import DiscogsService


@pytest.mark.asyncio
async def test_discogs_search_no_oauth_token(db_session: AsyncSession):
    """Test search returns empty when user has no OAuth token."""
    async with DiscogsService() as service:
        # Mock the OAuth auth check to return None
        with patch.object(service, "get_oauth_auth", return_value=None):
            results = await service.search(query="test", filters={}, db=db_session, user_id="non-existent-user-id")

            assert results == []


@pytest.mark.asyncio
async def test_discogs_search_with_oauth():
    """Test search works with proper OAuth setup."""
    async with DiscogsService() as service:
        # Mock the OAuth auth
        mock_auth = Mock()

        # Mock the API response
        mock_response = {
            "results": [
                {
                    "id": 123,
                    "type": "release",  # Required for the service to process
                    "title": "Test Album - Test Artist",
                    "year": "2023",
                    "format": ["Vinyl"],
                    "label": ["Test Label"],
                }
            ]
        }

        with patch.object(service, "get_oauth_auth", return_value=mock_auth):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value = AsyncMock(
                    status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
                )

                results = await service.search(
                    query="test",
                    filters={},
                    db=Mock(),  # Mock db session
                    user_id="test-user-id",
                )

                assert len(results) == 1
                assert results[0]["title"] == "Test Album - Test Artist"
                assert results[0]["artist"] == "Test Album"

                # Verify OAuth was used in the request
                mock_get.assert_called_once()
                _, kwargs = mock_get.call_args
                assert kwargs["auth"] == mock_auth


@pytest.mark.asyncio
async def test_discogs_search_with_filters():
    """Test search with various filters."""
    async with DiscogsService() as service:
        # Mock the OAuth auth
        mock_auth = Mock()

        # Mock empty response
        mock_response = {"results": []}

        with patch.object(service, "get_oauth_auth", return_value=mock_auth):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_get.return_value = AsyncMock(
                    status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
                )

                # Test with various filters
                filters = {
                    "limit": 100,
                    "page": 2,
                    "format": "Vinyl",
                    "genre": "Jazz",
                    "style": "Bebop",
                    "year_from": "1950",
                    "year_to": "1960",
                }

                await service.search(query="miles davis", filters=filters, db=Mock(), user_id="test-user-id")

                # Verify the API was called with correct params
                mock_get.assert_called_once()
                call_args = mock_get.call_args
                params = call_args[1]["params"]

                assert params["q"] == "miles davis"
                assert params["per_page"] == 100
                assert params["page"] == 2
                assert params["format"] == "Vinyl"
                assert params["genre"] == "Jazz"
                assert params["style"] == "Bebop"
                assert params["year"] == "1950-1960"
