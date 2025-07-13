"""Tests for SellerAnalysisService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SearchPlatform, SearchResult
from src.models.seller import Seller
from src.services.seller_analyzer import SellerAnalysisService


class TestSellerAnalysisService:
    """Test suite for SellerAnalysisService."""

    @pytest.fixture
    def service(self):
        """Create SellerAnalysisService instance."""
        return SellerAnalysisService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_seller(self):
        """Create sample seller for testing."""
        return Seller(
            id=str(uuid4()),
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="discogs123",
            seller_name="Vinyl Collector",
            location="Los Angeles, CA",
            country_code="US",
            feedback_score=Decimal("98.5"),
            total_feedback_count=1500,
            positive_feedback_percentage=Decimal("99.2"),
            ships_internationally=True,
            estimated_shipping_cost=Decimal("15.00"),
        )

    def test_normalize_country_code(self, service):
        """Test country code normalization."""
        # Test various location formats
        assert SellerAnalysisService.normalize_country_code("Los Angeles, CA") == "US"
        assert SellerAnalysisService.normalize_country_code("London, UK") == "UK"
        assert SellerAnalysisService.normalize_country_code("Toronto, Canada") == "CA"
        assert SellerAnalysisService.normalize_country_code("Berlin, Germany") == "EU"  # Germany is grouped under EU
        assert (
            SellerAnalysisService.normalize_country_code("Tokyo, Japan") == "OTHER"
        )  # Japan is not specifically handled
        assert SellerAnalysisService.normalize_country_code(None) == "OTHER"
        assert SellerAnalysisService.normalize_country_code("Random Location") == "OTHER"

    def test_extract_discogs_seller(self, service):
        """Test extracting seller info from Discogs data."""
        item_data = {
            "seller": {
                "id": "seller123",
                "username": "VinylShop",
                "location": "New York, NY",
                "rating": 99.5,
                "num_ratings": 150,
                "ships_to": {"international": True},
            }
        }

        seller_info = service._extract_discogs_seller(item_data)

        assert seller_info["platform_seller_id"] == "seller123"
        assert seller_info["seller_name"] == "VinylShop"
        assert seller_info["location"] == "New York, NY"
        assert seller_info["feedback_score"] == 99.5
        assert "ships_from" not in seller_info  # This field is not extracted

    def test_extract_ebay_seller(self, service):
        """Test extracting seller info from eBay data."""
        item_data = {
            "seller": {
                "username": "ebayseller456",
                "feedbackScore": 1234,
                "feedbackPercentage": "98.7%",
            },
            "itemLocation": {"country": "Chicago, IL"},
        }

        seller_info = service._extract_ebay_seller(item_data)

        assert seller_info["platform_seller_id"] == "ebayseller456"
        assert seller_info["seller_name"] == "ebayseller456"  # eBay uses username for both
        assert seller_info["location"] == "Chicago, IL"
        assert seller_info["feedback_score"] == 98.7
        assert seller_info["total_feedback_count"] == 1234

    def test_estimate_shipping_cost(self, service, sample_seller):
        """Test shipping cost estimation."""
        # Test base shipping cost for single item
        sample_seller.country_code = "US"
        cost = service.estimate_shipping_cost(
            seller=sample_seller, user_id="test_user", item_count=1, user_location="US"
        )
        assert cost == Decimal("5.00")  # Domestic US base rate

        # Test multiple items domestic
        cost = service.estimate_shipping_cost(
            seller=sample_seller, user_id="test_user", item_count=3, user_location="US"
        )
        # $5 base + (2 * $5 * 0.2) = $7
        assert cost == Decimal("7.00")

        # Test international shipping
        sample_seller.country_code = "UK"
        sample_seller.estimated_shipping_cost = None  # Clear seller estimate to test calculated cost
        cost = service.estimate_shipping_cost(
            seller=sample_seller, user_id="test_user", item_count=1, user_location="US"
        )
        assert cost == Decimal("25.00")  # International base rate

        # Test multiple items international
        cost = service.estimate_shipping_cost(
            seller=sample_seller, user_id="test_user", item_count=2, user_location="US"
        )
        # $25 base + (1 * $25 * 0.2) = $30
        assert cost == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_score_seller_reputation(self, service, sample_seller):
        """Test seller reputation scoring."""
        # Test excellent reputation
        sample_seller.feedback_score = Decimal("99.5")
        sample_seller.total_feedback_count = 1000
        score = await service.score_seller_reputation(sample_seller)
        assert score >= Decimal("90.0")  # Should be excellent

        # Test good reputation
        sample_seller.feedback_score = Decimal("97.0")
        sample_seller.total_feedback_count = 500
        sample_seller.positive_feedback_percentage = Decimal("95.0")  # Lower to get mid-range score
        score = await service.score_seller_reputation(sample_seller)
        # 50 base + 38.8 feedback + 25 count + 20 positive = 133.8 -> capped at 100
        assert score == Decimal("100.0")

        # Test new seller
        sample_seller.feedback_score = None
        sample_seller.total_feedback_count = 0
        sample_seller.positive_feedback_percentage = None  # New sellers have no feedback percentage
        score = await service.score_seller_reputation(sample_seller)
        assert score == Decimal("50.0")  # Default for new sellers

    @pytest.mark.asyncio
    async def test_calculate_location_preference_score(self, service, sample_seller):
        """Test location preference scoring."""
        # Test same country
        sample_seller.country_code = "US"
        score = await service.calculate_location_preference_score(seller=sample_seller, preferred_location="US")
        assert score == Decimal("100.0")

        # Test different countries but preference is ANY (gets normalized to OTHER)
        sample_seller.country_code = "UK"
        score = await service.calculate_location_preference_score(seller=sample_seller, preferred_location="ANY")
        assert score == Decimal("30.0")  # ANY gets normalized to OTHER, so penalty applies

        # Test different countries with specific preference
        sample_seller.country_code = "UK"
        score = await service.calculate_location_preference_score(seller=sample_seller, preferred_location="US")
        assert score == Decimal("10.0")  # Different location penalty

    @pytest.mark.asyncio
    async def test_find_or_create_seller_existing(self, service, mock_db, sample_seller):
        """Test finding existing seller."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_seller
        mock_db.execute.return_value = mock_result

        seller_info = {
            "platform_seller_id": "discogs123",
            "seller_name": "Vinyl Collector",
            "location": "Los Angeles, CA",
        }

        result = await service.find_or_create_seller(mock_db, SearchPlatform.DISCOGS, seller_info)

        assert result == sample_seller
        mock_db.add.assert_not_called()  # Should not create new seller

    @pytest.mark.asyncio
    async def test_find_or_create_seller_new(self, service, mock_db):
        """Test creating new seller."""
        # Mock database query - no existing seller
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock db operations
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        seller_info = {
            "platform_seller_id": "newseller",
            "seller_name": "New Record Shop",
            "location": "Boston, MA",
            "feedback_score": 100.0,
        }

        result = await service.find_or_create_seller(mock_db, SearchPlatform.EBAY, seller_info)

        assert result.platform_seller_id == "newseller"
        assert result.seller_name == "New Record Shop"
        assert result.location == "Boston, MA"
        assert result.country_code == "US"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_seller_inventory(self, service, mock_db, sample_seller):
        """Test analyzing seller inventory."""
        user_id = str(uuid4())

        # Remove seller estimated shipping to test our calculation
        sample_seller.estimated_shipping_cost = None

        # Mock search results
        search_results = [
            SearchResult(
                id=str(uuid4()),
                seller_id=sample_seller.id,
                item_price=Decimal("25.00"),
                is_in_wantlist=True,
                is_in_collection=False,
            ),
            SearchResult(
                id=str(uuid4()),
                seller_id=sample_seller.id,
                item_price=Decimal("30.00"),
                is_in_wantlist=True,
                is_in_collection=False,
            ),
            SearchResult(
                id=str(uuid4()),
                seller_id=sample_seller.id,
                item_price=Decimal("20.00"),
                is_in_wantlist=False,
                is_in_collection=False,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = search_results
        mock_db.execute.return_value = mock_result

        # Mock inventory operations
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        analysis = await service.analyze_seller_inventory(mock_db, sample_seller, user_id)

        assert analysis["total_items"] == 3
        assert analysis["wantlist_items"] == 2
        assert analysis["total_value"] == Decimal("75.00")
        assert analysis["estimated_shipping"] == Decimal("7.0")  # 3 items domestic: $5 + (2 * $5 * 0.2) = $7

    def test_calculate_shipping_savings(self, service, sample_seller):
        """Test shipping savings calculation."""
        # Test multiple items
        sample_seller.estimated_shipping_cost = None  # Use calculated shipping
        sample_seller.country_code = "US"  # Ensure US domestic shipping
        savings = service.calculate_shipping_savings(3, sample_seller)
        # Individual: 3 * $5 = $15, Combined: $5 + (2 * $5 * 0.2) = $7, Savings: $8
        assert savings == Decimal("8.00")

        # Test single item - no savings
        savings = service.calculate_shipping_savings(1, sample_seller)
        assert savings == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_find_multi_item_opportunities(self, service, mock_db, sample_seller):
        """Test finding multi-item seller opportunities."""
        search_id = str(uuid4())

        # Mock sellers with multiple items
        from collections import namedtuple

        SellerRow = namedtuple("SellerRow", ["seller_id", "item_count", "total_value", "wantlist_count"])

        seller_id1 = str(uuid4())
        seller_id2 = str(uuid4())

        # Only return sellers that meet the min_items criteria
        sellers = [
            SellerRow(seller_id=seller_id1, item_count=3, total_value=Decimal("90.00"), wantlist_count=2),
            SellerRow(seller_id=seller_id2, item_count=5, total_value=Decimal("150.00"), wantlist_count=4),
        ]

        # Mock first query (multi-item sellers)
        mock_result = MagicMock()
        mock_result.all.return_value = sellers

        # Create mock sellers
        seller1 = MagicMock()
        seller1.id = seller_id1
        seller1.country_code = "US"
        seller1.estimated_shipping_cost = None

        seller2 = MagicMock()
        seller2.id = seller_id2
        seller2.country_code = "US"
        seller2.estimated_shipping_cost = None

        # Mock subsequent seller lookups
        mock_seller_result1 = MagicMock()
        mock_seller_result1.scalar_one_or_none.return_value = seller1

        mock_seller_result2 = MagicMock()
        mock_seller_result2.scalar_one_or_none.return_value = seller2

        # Set up execute to return different results based on call count
        mock_db.execute.side_effect = [mock_result, mock_seller_result1, mock_seller_result2]

        opportunities = await service.find_multi_item_opportunities(mock_db, search_id, min_items=2)

        assert len(opportunities) == 2  # Only sellers with 2+ items
        assert opportunities[0]["item_count"] == 3
        assert opportunities[0]["total_value"] == Decimal("90.00")
        assert opportunities[0]["wantlist_count"] == 2
        assert opportunities[1]["item_count"] == 5
        assert opportunities[1]["total_value"] == Decimal("150.00")
        assert opportunities[1]["wantlist_count"] == 4
