from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.discogs import DiscogsService
from tests.mocks.discogs_marketplace_mocks import DiscogsMarketplaceMockGenerator


@pytest.mark.asyncio
async def test_discogs_search_no_oauth_token(db_session: AsyncSession):
    """Test search works without OAuth token using marketplace scraper."""
    # Mock the marketplace scraper
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Mock empty search results
        mock_scraper_instance.search_marketplace.return_value = DiscogsMarketplaceMockGenerator.generate_empty_results()

        async with DiscogsService() as service:
            results = await service.search(query="test", filters={}, db=db_session, user_id="non-existent-user-id")

            # Should return empty results when scraper returns empty
            assert results == []


@pytest.mark.asyncio
async def test_discogs_search_with_oauth(db_session: AsyncSession):
    """Test search works with marketplace scraper."""
    # Mock the marketplace scraper
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Mock search results
        mock_scraper_instance.search_marketplace.return_value = (
            DiscogsMarketplaceMockGenerator.generate_mock_search_results(
                "Test Artist - Test Album", page=1, limit=1, total=1
            )
        )

        async with DiscogsService() as service:
            results = await service.search(
                query="test",
                filters={},
                db=db_session,
                user_id="test-user-id",
            )

            assert len(results) == 1
            assert "Test Artist" in results[0]["artist"]
            assert "Test Album" in results[0]["album"]

            # Verify scraper was called
            mock_scraper_instance.search_marketplace.assert_called_once()


@pytest.mark.asyncio
async def test_discogs_search_with_filters(db_session: AsyncSession):
    """Test search with various filters."""
    # Mock the marketplace scraper
    with patch("src.services.discogs_marketplace_scraper.DiscogsMarketplaceScraper") as MockScraper:
        mock_scraper_instance = AsyncMock()
        MockScraper.return_value.__aenter__.return_value = mock_scraper_instance

        # Mock empty response
        mock_scraper_instance.search_marketplace.return_value = DiscogsMarketplaceMockGenerator.generate_empty_results()

        async with DiscogsService() as service:
            # Test with various filters
            filters = {
                "limit": 100,
                "page": 2,
                "min_record_condition": "Good Plus (G+)",
                "genre": "Jazz",
                "style": "Bebop",
                "year_from": "1950",
                "year_to": "1960",
            }

            await service.search(query="miles davis", filters=filters, db=db_session, user_id="test-user-id")

            # Verify the scraper was called with correct params
            mock_scraper_instance.search_marketplace.assert_called_once()
            call_args = mock_scraper_instance.search_marketplace.call_args

            # Check that filters were properly transformed
            scraper_filters = call_args[0][1]  # Second positional argument
            assert scraper_filters["condition"] == "Good Plus (G+)"
            assert scraper_filters["genre"] == "Jazz"
            assert scraper_filters["style"] == "Bebop"
            assert scraper_filters["year_from"] == "1950"
            assert scraper_filters["year_to"] == "1960"
            assert scraper_filters["format"] == "Vinyl"

            # Check pagination
            assert call_args[0][2] == 2  # page
            assert call_args[0][3] == 100  # limit
