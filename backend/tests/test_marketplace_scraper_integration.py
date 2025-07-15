"""Integration tests for Discogs marketplace scraper."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.discogs import DiscogsService
from tests.mocks.discogs_marketplace_mocks import DiscogsMarketplaceMockGenerator


@pytest.mark.asyncio
async def test_marketplace_search_integration(db_session: AsyncSession):
    """Test that DiscogsService properly integrates with marketplace scraper."""
    # Mock the marketplace scraper
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Generate mock results
        mock_results = DiscogsMarketplaceMockGenerator.generate_mock_search_results(
            "Pink Floyd - Dark Side", page=1, limit=2, total=5
        )
        mock_scraper_instance.search_marketplace.return_value = mock_results

        async with DiscogsService() as service:
            # Search with basic query
            results = await service.search(
                query="Pink Floyd Dark Side", filters={}, db=db_session, user_id="test-user-id"
            )

            # Verify results are properly formatted
            assert len(results) == 2
            assert all(isinstance(r, dict) for r in results)

            # Check required fields
            for result in results:
                assert "id" in result
                assert "title" in result
                assert "artist" in result
                assert "price" in result
                assert "seller" in result
                assert "condition" in result

            # Verify scraper was called correctly
            mock_scraper_instance.search_marketplace.assert_called_once_with(
                "Pink Floyd Dark Side", {"format": "Vinyl"}, 1, 50
            )


@pytest.mark.asyncio
async def test_marketplace_search_with_advanced_filters(db_session: AsyncSession):
    """Test marketplace search with various filter combinations."""
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Return empty results for this test
        mock_scraper_instance.search_marketplace.return_value = {
            "items": [],
            "total": 0,
            "page": {"current": 1, "limit": 50, "total_pages": 0},
        }

        async with DiscogsService() as service:
            # Test with all filter types
            filters = {
                "min_record_condition": "Very Good Plus (VG+)",
                "seller_location_preference": "US",
                "genre": "Rock",
                "style": "Psychedelic Rock",
                "min_price": 10,
                "max_price": 100,
                "year_from": "1970",
                "year_to": "1975",
                "page": 2,
                "limit": 100,
            }

            await service.search(query="test query", filters=filters, db=db_session, user_id="test-user-id")

            # Verify scraper was called with properly mapped filters
            call_args = mock_scraper_instance.search_marketplace.call_args
            query_arg = call_args[0][0]
            filter_arg = call_args[0][1]
            page_arg = call_args[0][2]
            limit_arg = call_args[0][3]

            assert query_arg == "test query"
            assert filter_arg["condition"] == "Very Good Plus (VG+)"
            assert filter_arg["seller_location_preference"] == "US"
            assert filter_arg["genre"] == "Rock"
            assert filter_arg["style"] == "Psychedelic Rock"
            assert filter_arg["price_min"] == 10
            assert filter_arg["price_max"] == 100
            assert filter_arg["year_from"] == "1970"
            assert filter_arg["year_to"] == "1975"
            assert filter_arg["format"] == "Vinyl"
            assert page_arg == 2
            assert limit_arg == 100


@pytest.mark.asyncio
async def test_marketplace_scraper_error_handling(db_session: AsyncSession):
    """Test error handling when marketplace scraper fails."""
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Simulate scraper error
        mock_scraper_instance.search_marketplace.return_value = {"error": "Failed to connect to Discogs", "items": []}

        async with DiscogsService() as service:
            results = await service.search(query="test", filters={}, db=db_session, user_id="test-user-id")

            # Should return empty results on error
            assert results == []


@pytest.mark.asyncio
async def test_marketplace_result_formatting(db_session: AsyncSession):
    """Test that marketplace results are properly formatted for VinylDigger."""
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Create a single detailed mock result
        mock_scraper_instance.search_marketplace.return_value = {
            "items": [
                {
                    "id": "12345",
                    "release_id": "67890",
                    "title": "The Beatles - Abbey Road",
                    "artist": "The Beatles",
                    "album": "Abbey Road",
                    "year": 1969,
                    "format": ["Vinyl", "LP", "Album"],
                    "label": ["Apple Records"],
                    "catno": "PCS 7088",
                    "price": 45.99,
                    "currency": "USD",
                    "condition": "Near Mint (NM or M-)",
                    "sleeve_condition": "Very Good Plus (VG+)",
                    "seller": {
                        "id": "seller123",
                        "username": "VinylLover",
                        "rating": 99.5,
                        "url": "https://www.discogs.com/seller/VinylLover",
                    },
                    "shipping_price": 5.99,
                    "location": "United States",
                    "allow_offers": True,
                    "community": {"have": 150000, "want": 50000},
                    "thumb": "https://example.com/thumb.jpg",
                    "cover_image": "https://example.com/cover.jpg",
                }
            ],
            "total": 1,
            "page": {"current": 1, "limit": 50, "total_pages": 1},
        }

        async with DiscogsService() as service:
            results = await service.search(
                query="Beatles Abbey Road", filters={}, db=db_session, user_id="test-user-id"
            )

            # Verify the result is properly formatted
            assert len(results) == 1
            result = results[0]

            # Check all expected fields are present
            assert result["id"] == "12345"
            assert result["release_id"] == "67890"
            assert result["title"] == "The Beatles - Abbey Road"
            assert result["artist"] == "The Beatles"
            assert result["album"] == "Abbey Road"
            assert result["year"] == 1969
            assert result["price"] == 45.99
            assert result["currency"] == "USD"
            assert result["condition"] == "Near Mint (NM or M-)"
            assert result["sleeve_condition"] == "Very Good Plus (VG+)"

            # Check seller info
            assert result["seller"]["username"] == "VinylLover"
            assert result["seller"]["rating"] == 99.5

            # Check additional fields
            assert result["shipping_price"] == 5.99
            assert result["location"] == "United States"
            assert result["allow_offers"] is True
