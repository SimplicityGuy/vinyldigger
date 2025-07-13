"""Tests for SellerAnalysisService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SearchPlatform, SearchResult
from src.models.search_analysis import SellerAnalysis
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
            id="seller-1",
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

    @pytest.fixture
    def sample_search_results(self, sample_seller):
        """Create sample search results for testing."""
        return [
            SearchResult(
                id=f"result-{i}",
                search_id="search-1",
                platform=SearchPlatform.DISCOGS,
                item_id=f"item-{i}",
                seller_id=sample_seller.id,
                item_price=Decimal(f"{20 + i * 5}.00"),
                item_condition="VG+",
                item_data={"title": f"Album {i}", "artist": "Test Artist", "year": 2000 + i, "format": "Vinyl"},
                is_in_wantlist=(i % 2 == 0),  # Every other item in wantlist
                is_in_collection=False,
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_estimate_shipping_cost_domestic(self, service, sample_seller):
        """Test shipping cost estimation for domestic shipping."""
        # Same country shipping
        sample_seller.country_code = "US"
        cost = await service.estimate_shipping_cost(sample_seller, "user-1", 1, "US")
        assert cost == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_estimate_shipping_cost_international(self, service, sample_seller):
        """Test shipping cost estimation for international shipping."""
        # US to Europe
        sample_seller.country_code = "US"
        cost = await service.estimate_shipping_cost(sample_seller, "user-1", 1, "Germany")
        assert cost == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_estimate_shipping_cost_multiple_items(self, service, sample_seller):
        """Test shipping cost estimation for multiple items."""
        sample_seller.country_code = "US"
        cost = await service.estimate_shipping_cost(sample_seller, "user-1", 3, "US")
        # Base cost (5.00) + 2 additional items * 20% = 5.00 + 2.00 = 7.00
        assert cost == Decimal("7.00")

    @pytest.mark.asyncio
    async def test_find_or_create_seller_existing(self, service, mock_db, sample_seller):
        """Test finding existing seller."""
        # Mock existing seller found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_seller
        mock_db.execute.return_value = mock_result

        # Test finding existing seller
        result = await service.find_or_create_seller(
            mock_db, SearchPlatform.DISCOGS, "discogs123", "Vinyl Collector", "Los Angeles, CA"
        )

        assert result == sample_seller
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_or_create_seller_new(self, service, mock_db):
        """Test creating new seller."""
        # Mock no existing seller found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Test creating new seller
        result = await service.find_or_create_seller(
            mock_db, SearchPlatform.EBAY, "ebay456", "Record Store", "New York, NY"
        )

        assert isinstance(result, Seller)
        assert result.platform == SearchPlatform.EBAY
        assert result.platform_seller_id == "ebay456"
        assert result.seller_name == "Record Store"
        assert result.location == "New York, NY"
        mock_db.add.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_analyze_seller_inventory(self, service, mock_db, sample_seller, sample_search_results):
        """Test analyzing seller inventory."""
        # Mock database queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_search_results
        mock_db.execute.return_value = mock_result

        # Test inventory analysis
        analysis = await service.analyze_seller_inventory(mock_db, "search-1", sample_seller, "user-1")

        assert isinstance(analysis, SellerAnalysis)
        assert analysis.seller_id == sample_seller.id
        assert analysis.total_items == 5
        assert analysis.wantlist_items == 3  # Every other item (0, 2, 4)
        assert analysis.total_value == Decimal("110.00")  # 20+25+30+35+40
        assert analysis.avg_item_price == Decimal("22.00")  # 110/5

    def test_calculate_price_competitiveness_best_price(self, service):
        """Test price competitiveness calculation for best price."""
        # Seller has the lowest price
        score = service.calculate_price_competitiveness(
            avg_seller_price=Decimal("20.00"), market_min_price=Decimal("20.00"), market_avg_price=Decimal("30.00")
        )
        assert score == Decimal("100.0")

    def test_calculate_price_competitiveness_average_price(self, service):
        """Test price competitiveness calculation for average price."""
        # Seller at market average
        score = service.calculate_price_competitiveness(
            avg_seller_price=Decimal("30.00"), market_min_price=Decimal("20.00"), market_avg_price=Decimal("30.00")
        )
        assert score == Decimal("50.0")

    def test_calculate_price_competitiveness_high_price(self, service):
        """Test price competitiveness calculation for high price."""
        # Seller above market average
        score = service.calculate_price_competitiveness(
            avg_seller_price=Decimal("40.00"), market_min_price=Decimal("20.00"), market_avg_price=Decimal("30.00")
        )
        assert score == Decimal("0.0")

    def test_calculate_inventory_depth_score(self, service):
        """Test inventory depth score calculation."""
        # Single item
        score = service.calculate_inventory_depth_score(1, 0)
        assert score == Decimal("20.0")

        # Multiple items with wantlist matches
        score = service.calculate_inventory_depth_score(5, 3)
        assert score == Decimal("85.0")  # 40 + 45

        # Many items
        score = service.calculate_inventory_depth_score(20, 5)
        assert score == Decimal("100.0")  # Capped at 100

    def test_calculate_seller_reputation_score_excellent(self, service):
        """Test seller reputation calculation for excellent seller."""
        score = service.calculate_seller_reputation_score(
            feedback_score=Decimal("99.5"), total_feedback=2000, positive_percentage=Decimal("99.8")
        )
        assert score >= Decimal("90.0")

    def test_calculate_seller_reputation_score_good(self, service):
        """Test seller reputation calculation for good seller."""
        score = service.calculate_seller_reputation_score(
            feedback_score=Decimal("95.0"), total_feedback=500, positive_percentage=Decimal("98.0")
        )
        assert Decimal("70.0") <= score <= Decimal("90.0")

    def test_calculate_seller_reputation_score_new_seller(self, service):
        """Test seller reputation calculation for new seller."""
        score = service.calculate_seller_reputation_score(
            feedback_score=None, total_feedback=10, positive_percentage=Decimal("100.0")
        )
        assert score <= Decimal("50.0")

    def test_calculate_location_preference_score_same_country(self, service):
        """Test location preference for same country."""
        score = service.calculate_location_preference_score("US", "US")
        assert score == Decimal("100.0")

    def test_calculate_location_preference_score_same_region(self, service):
        """Test location preference for same region."""
        score = service.calculate_location_preference_score("US", "CA")
        assert score == Decimal("75.0")

    def test_calculate_location_preference_score_different_region(self, service):
        """Test location preference for different region."""
        score = service.calculate_location_preference_score("US", "EU")
        assert score == Decimal("40.0")

    def test_calculate_overall_score(self, service):
        """Test overall score calculation with weights."""
        score = service.calculate_overall_score(
            price_competitiveness=Decimal("80.0"),
            inventory_depth=Decimal("70.0"),
            seller_reputation=Decimal("90.0"),
            location_preference=Decimal("100.0"),
        )

        # Verify weighted calculation
        expected = (
            Decimal("80.0") * Decimal("0.35")  # price_competitiveness
            + Decimal("70.0") * Decimal("0.25")  # inventory_depth
            + Decimal("90.0") * Decimal("0.20")  # seller_reputation
            + Decimal("100.0") * Decimal("0.20")  # location_preference
        )
        assert abs(score - expected) < Decimal("0.1")

    @pytest.mark.asyncio
    async def test_process_search_sellers(self, service, mock_db, sample_search_results):
        """Test processing all sellers from search results."""
        # Mock database operations
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = None  # New seller
        mock_db.execute.return_value = mock_seller_result

        # Test processing sellers
        sellers = await service.process_search_sellers(mock_db, sample_search_results)

        # Should create one seller (all results have same seller_id)
        assert len(sellers) == 1
        assert isinstance(sellers[0], Seller)

    def test_get_country_from_location(self, service):
        """Test extracting country code from location."""
        # US locations
        assert service.get_country_from_location("Los Angeles, CA") == "US"
        assert service.get_country_from_location("New York, NY") == "US"

        # Canadian locations
        assert service.get_country_from_location("Toronto, ON") == "CA"
        assert service.get_country_from_location("Vancouver, BC") == "CA"

        # UK locations
        assert service.get_country_from_location("London, England") == "UK"
        assert service.get_country_from_location("Manchester, UK") == "UK"

        # European locations
        assert service.get_country_from_location("Berlin, Germany") == "EU"
        assert service.get_country_from_location("Paris, France") == "EU"

        # Unknown location
        assert service.get_country_from_location("Unknown Location") == "XX"
