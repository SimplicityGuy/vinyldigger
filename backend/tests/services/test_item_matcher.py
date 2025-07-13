"""Tests for ItemMatchingService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.item_match import ItemMatch, ItemMatchResult, MatchConfidence
from src.services.item_matcher import ItemMatchingService


class TestItemMatchingService:
    """Test suite for ItemMatchingService."""

    @pytest.fixture
    def service(self):
        """Create ItemMatchingService instance."""
        return ItemMatchingService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    def test_normalize_text(self, service):
        """Test text normalization for matching."""
        # Test basic normalization
        result = service.normalize_text("The Beatles - Abbey Road (Remastered)")
        assert result == "beatles abbey road remastered"

        # Test special characters and numbers
        result = service.normalize_text("Led Zeppelin IV (1971) [180g Vinyl]")
        assert result == "led zeppelin iv 1971 180g vinyl"

        # Test multiple spaces and punctuation
        result = service.normalize_text("Pink Floyd  -  Dark Side of the Moon...")
        assert result == "pink floyd dark side moon"

    def test_calculate_similarity(self, service):
        """Test similarity calculation between texts."""
        # Exact match
        similarity = service.calculate_similarity("Abbey Road", "Abbey Road")
        assert similarity == 100.0

        # Similar strings
        similarity = service.calculate_similarity("Abbey Road", "Abbey Road Remastered")
        assert 50.0 < similarity < 100.0  # Adjusted threshold

        # Different strings
        similarity = service.calculate_similarity("Abbey Road", "Dark Side of the Moon")
        assert similarity < 50.0

        # Empty strings
        similarity = service.calculate_similarity("", "")
        assert similarity == 0.0  # Empty strings return 0.0

    def test_generate_fingerprint(self, service):
        """Test fingerprint creation for matching."""
        fingerprint = service.generate_fingerprint("Abbey Road", "The Beatles", 1969, "PCS 7088")
        # Should be deterministic and consistent
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 32  # SHA256 hash truncated to 32 chars

        # Same inputs should produce same fingerprint
        fingerprint2 = service.generate_fingerprint("Abbey Road", "The Beatles", 1969, "PCS 7088")
        assert fingerprint == fingerprint2

        # Different inputs should produce different fingerprints
        fingerprint3 = service.generate_fingerprint("Help!", "The Beatles", 1965, "PMC 1255")
        assert fingerprint != fingerprint3

    @pytest.mark.asyncio
    async def test_find_or_create_item_match_existing(self, service, mock_db):
        """Test finding existing item match."""
        # Setup mock existing match
        existing_match = ItemMatch(
            id="test-id",
            canonical_title="Abbey Road",
            canonical_artist="The Beatles",
            canonical_year=1969,
            canonical_format="Vinyl",
            match_fingerprint="test-fingerprint",
            total_matches=1,
            avg_confidence_score=Decimal("95.0"),
        )

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_match
        mock_db.execute.return_value = mock_result

        # Test finding existing match
        item_info = {"title": "Abbey Road", "artist": "The Beatles", "year": 1969, "format": "Vinyl"}
        result = await service.find_or_create_item_match(mock_db, item_info)

        assert result == existing_match
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_or_create_item_match_new(self, service, mock_db):
        """Test creating new item match."""
        # Mock no existing match found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock flush
        mock_db.flush = AsyncMock()

        # Test creating new match
        item_info = {"title": "Abbey Road", "artist": "The Beatles", "year": 1969, "format": "Vinyl"}
        result = await service.find_or_create_item_match(mock_db, item_info)

        assert isinstance(result, ItemMatch)
        assert result.canonical_title == "Abbey Road"
        assert result.canonical_artist == "The Beatles"
        assert result.canonical_year == 1969
        assert result.canonical_format == "Vinyl"
        mock_db.add.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_match_search_result_success(self, service, mock_db):
        """Test matching search result successfully."""
        # Mock database operations
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # New match
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        # Test data
        item_data = {"title": "Abbey Road", "artist": "The Beatles", "year": 1969, "format": "Vinyl"}

        # Test matching
        match_result = await service.match_search_result(mock_db, "search-result-id", item_data, "discogs")

        assert isinstance(match_result, ItemMatchResult)
        assert match_result.search_result_id == "search-result-id"
        assert isinstance(match_result.confidence, MatchConfidence)
        assert match_result.confidence_score >= 0.0
        mock_db.add.assert_called()

    def test_extract_item_info_discogs(self, service):
        """Test extracting item info from Discogs data."""
        discogs_data = {
            "title": "Abbey Road",
            "artists": [{"name": "The Beatles"}],
            "year": 1969,
            "formats": [{"name": "Vinyl"}],
            "labels": [{"catno": "PCS 7088"}],
            "price": 25.00,
            "condition": "VG+",
        }

        info = service.extract_item_info(discogs_data, "discogs")

        assert info["title"] == "Abbey Road"
        assert info["artist"] == "The Beatles"
        assert info["year"] == 1969
        assert info["format"] == "Vinyl"
        assert info["catalog_number"] == "PCS 7088"

    def test_extract_item_info_ebay(self, service):
        """Test extracting item info from eBay data."""
        ebay_data = {
            "title": "The Beatles - Abbey Road",
            "year": 1969,
            "format": "Vinyl",
            "price": {"value": 30.00},
            "condition": "Used",
        }

        info = service.extract_item_info(ebay_data, "ebay")

        assert info["title"] == "Abbey Road"
        assert info["artist"] == "The Beatles"
        assert info["year"] == 1969
        assert info["format"] == "Vinyl"
        assert info["price"] == 30.00

    @pytest.mark.asyncio
    async def test_calculate_match_confidence(self, service):
        """Test confidence calculation."""
        # Create mock item match
        item_match = ItemMatch(
            canonical_title="Abbey Road",
            canonical_artist="The Beatles",
            canonical_year=1969,
            canonical_format="Vinyl",
            catalog_number="PCS 7088",
        )

        # Test with identical info
        item_info = {
            "title": "Abbey Road",
            "artist": "The Beatles",
            "year": 1969,
            "format": "Vinyl",
            "catalog_number": "PCS 7088",
        }

        confidence, score, metadata = await service.calculate_match_confidence(item_match, item_info)

        assert isinstance(confidence, MatchConfidence)
        assert score > 0.0
        assert isinstance(metadata, dict)
        assert "title_similarity" in metadata
        assert "artist_similarity" in metadata
