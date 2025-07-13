"""Tests for RecommendationEngine."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import (
    DealScore,
    RecommendationType,
    SearchResultAnalysis,
    SellerAnalysis,
)
from src.models.seller import Seller
from src.services.recommendation_engine import RecommendationEngine


class TestRecommendationEngine:
    """Test suite for RecommendationEngine."""

    @pytest.fixture
    def engine(self):
        """Create RecommendationEngine instance."""
        return RecommendationEngine()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results."""
        return [
            SearchResult(
                id=str(uuid4()),
                search_id=str(uuid4()),
                platform=SearchPlatform.DISCOGS,
                item_id="disc123",
                item_price=Decimal("25.00"),
                item_condition="VG+",
                seller_id=str(uuid4()),
                is_in_wantlist=True,
                item_data={"title": "Abbey Road", "artist": "The Beatles", "year": 1969},
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=str(uuid4()),
                platform=SearchPlatform.EBAY,
                item_id="ebay456",
                item_price=Decimal("30.00"),
                item_condition="NM",
                seller_id=str(uuid4()),
                is_in_wantlist=True,
                item_data={"title": "Help!", "artist": "The Beatles", "year": 1965},
            ),
        ]

    def test_determine_deal_score_excellent(self, engine):
        """Test deal score calculation for excellent deals."""
        score = engine._determine_deal_score(Decimal("92.0"))
        assert score == DealScore.EXCELLENT

    def test_determine_deal_score_very_good(self, engine):
        """Test deal score calculation for very good deals."""
        score = engine._determine_deal_score(Decimal("82.0"))
        assert score == DealScore.VERY_GOOD

    def test_determine_deal_score_good(self, engine):
        """Test deal score calculation for good deals."""
        score = engine._determine_deal_score(Decimal("72.0"))
        assert score == DealScore.GOOD

    def test_determine_deal_score_fair(self, engine):
        """Test deal score calculation for fair deals."""
        score = engine._determine_deal_score(Decimal("62.0"))
        assert score == DealScore.FAIR

    def test_determine_deal_score_poor(self, engine):
        """Test deal score calculation for poor deals."""
        score = engine._determine_deal_score(Decimal("45.0"))
        assert score == DealScore.POOR

    def test_calculate_inventory_depth_score(self, engine):
        """Test inventory depth score calculation."""
        # High ratio of wantlist items
        score = engine._calculate_inventory_depth_score(total_items=5, wantlist_items=4)
        assert score >= Decimal("80.0")

        # Medium ratio
        score = engine._calculate_inventory_depth_score(total_items=3, wantlist_items=1)
        # 3 items = base 80, 1 wantlist = +10 bonus = 90
        assert score == Decimal("90.0")

        # Low ratio
        score = engine._calculate_inventory_depth_score(total_items=1, wantlist_items=0)
        assert score <= Decimal("30.0")

    @pytest.mark.asyncio
    async def test_analyze_search_results(self, engine, mock_db, sample_search_results):
        """Test analyzing search results."""
        search_id = str(uuid4())
        user_id = str(uuid4())

        # Mock saved search
        search = SavedSearch(
            id=search_id, user_id=user_id, name="Test Search", query="test", platform=SearchPlatform.BOTH
        )

        # Mock database queries
        mock_search_result = MagicMock()
        mock_search_result.scalar_one_or_none.return_value = search

        mock_results = MagicMock()
        mock_results.scalars.return_value.all.return_value = sample_search_results

        # Mock seller lookups - one for each unique seller in results
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = None  # No existing seller

        # Mock top sellers query for recommendations
        mock_top_sellers = MagicMock()
        mock_top_sellers.scalars.return_value.all.return_value = []  # No seller analyses

        # Execute will be called multiple times, return appropriate results
        # 1. Get saved search
        # 2. Get search results
        # 3-4. Get sellers (one for each unique seller)
        # 5. Get top sellers for recommendations
        mock_db.execute.side_effect = [
            mock_search_result,
            mock_results,
            mock_seller_result,
            mock_seller_result,
            mock_top_sellers,
        ]

        # Mock seller analyzer methods
        with patch.object(engine.seller_analyzer, "find_or_create_seller") as mock_find_seller:
            # Create a proper mock seller
            mock_seller = MagicMock()
            mock_seller.id = str(uuid4())
            mock_seller.total_feedback_count = 100  # Set numeric value
            mock_seller.feedback_score = Decimal("98.5")
            mock_seller.positive_feedback_percentage = Decimal("98.5")
            mock_find_seller.return_value = mock_seller

            with patch.object(engine.seller_analyzer, "analyze_seller_inventory") as mock_inventory:
                mock_inventory.return_value = {
                    "total_items": 2,
                    "wantlist_items": 2,
                    "total_value": Decimal("55.00"),
                    "estimated_shipping": Decimal("5.00"),
                }

                with patch.object(engine.seller_analyzer, "find_multi_item_opportunities") as mock_multi:
                    mock_multi.return_value = []

                    # Mock db operations
                    mock_db.add = MagicMock()
                    mock_db.commit = AsyncMock()
                    mock_db.refresh = AsyncMock()

                    analysis = await engine.analyze_search_results(mock_db, search_id, user_id)

            assert analysis.total_results == 2
            assert analysis.wantlist_matches == 2
            assert analysis.min_price == Decimal("25.00")
            assert analysis.max_price == Decimal("30.00")
            assert analysis.avg_price == Decimal("27.50")

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, engine, mock_db):
        """Test recommendation generation."""
        search_id = str(uuid4())
        user_id = str(uuid4())

        # Create search and analysis objects
        search = SavedSearch(
            id=search_id, user_id=user_id, name="Test Search", query="test query", platform=SearchPlatform.BOTH
        )

        analysis = SearchResultAnalysis(
            id=str(uuid4()),
            search_id=search_id,
            total_results=10,
            total_sellers=3,
            multi_item_sellers=2,
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"),
            avg_price=Decimal("30.00"),
            wantlist_matches=5,
            collection_duplicates=1,
            new_discoveries=4,
        )

        # Create sample seller analyses
        seller_analyses = [
            SellerAnalysis(
                id=str(uuid4()),
                search_analysis_id=analysis.id,
                seller_id=str(uuid4()),
                total_items=3,
                wantlist_items=2,
                total_value=Decimal("75.00"),
                avg_item_price=Decimal("25.00"),
                estimated_shipping=Decimal("15.00"),
                price_competitiveness=Decimal("85.0"),
                inventory_depth_score=Decimal("80.0"),
                seller_reputation_score=Decimal("90.0"),
                location_preference_score=Decimal("100.0"),
                overall_score=Decimal("88.0"),
                recommendation_rank=1,
            )
        ]

        # Mock database queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = seller_analyses
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        seller = Seller(
            id=seller_analyses[0].seller_id,
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller123",
            seller_name="Test Seller",
            location="Los Angeles, CA",
            country_code="US",
            feedback_score=Decimal("98.5"),
        )

        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = seller

        # Mock search results for the seller
        mock_results = MagicMock()
        mock_results.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_result, mock_seller_result, mock_results]

        # The method saves recommendations to DB but doesn't return them
        await engine._generate_recommendations(mock_db, analysis, search, user_id)

        # Verify db.add was called to add recommendations
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_create_multi_item_recommendation(self, engine, mock_db):
        """Test creating multi-item deal recommendation."""
        analysis = SearchResultAnalysis(
            id=str(uuid4()),
            search_id=str(uuid4()),
            total_results=10,
            total_sellers=3,
            multi_item_sellers=1,
            avg_price=Decimal("30.00"),
        )

        seller = Seller(
            id=str(uuid4()),
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller123",
            seller_name="Vinyl Paradise",
            location="New York, NY",
            country_code="US",
        )

        seller_analysis = SellerAnalysis(
            id=str(uuid4()),
            search_analysis_id=analysis.id,
            seller_id=seller.id,
            total_items=5,
            wantlist_items=3,
            total_value=Decimal("150.00"),
            estimated_shipping=Decimal("15.00"),
            overall_score=Decimal("85.0"),
        )

        # Create seller items instead of mocking DB
        seller_items = [
            SearchResult(
                id=str(uuid4()),
                search_id=analysis.search_id,
                seller_id=seller.id,
                is_in_wantlist=True,
                item_price=Decimal("30.00"),
                item_condition="VG+",
                platform=SearchPlatform.DISCOGS,
                item_id=f"disc{i}",
                item_data={"title": f"Test Album {i}", "artist": "Test Artist"},
            )
            for i in range(3)
        ]

        rec = engine._create_multi_item_recommendation(analysis, seller, seller_analysis, seller_items)

        assert rec.recommendation_type == RecommendationType.MULTI_ITEM_DEAL
        assert rec.total_items == 5
        assert rec.wantlist_items == 3
        assert rec.seller_id == seller.id
        assert rec.deal_score == DealScore.VERY_GOOD  # 85.0 score falls in VERY_GOOD range

    @pytest.mark.asyncio
    async def test_create_best_price_recommendation(self, engine, mock_db):
        """Test creating best price recommendation."""
        analysis = SearchResultAnalysis(
            id=str(uuid4()), search_id=str(uuid4()), total_results=10, avg_price=Decimal("35.00")
        )

        seller = Seller(
            id=str(uuid4()), platform=SearchPlatform.EBAY, platform_seller_id="ebayseller", seller_name="Deals4You"
        )

        seller_analysis = SellerAnalysis(
            id=str(uuid4()),
            search_analysis_id=analysis.id,
            seller_id=seller.id,
            total_items=1,
            wantlist_items=1,
            total_value=Decimal("25.00"),
            estimated_shipping=Decimal("10.00"),
            price_competitiveness=Decimal("95.0"),
            overall_score=Decimal("90.0"),
        )

        # Create seller items
        seller_items = [
            SearchResult(
                id=str(uuid4()),
                search_id=analysis.search_id,
                seller_id=seller.id,
                item_id="test1",
                item_price=Decimal("25.00"),
                item_condition="NM",
                platform=SearchPlatform.EBAY,
                is_in_wantlist=True,
                item_data={"title": "Test Album", "artist": "Test Artist"},
            )
        ]

        rec = engine._create_best_price_recommendation(analysis, seller, seller_analysis, seller_items)

        assert rec.recommendation_type == RecommendationType.BEST_PRICE
        assert rec.total_items == 1
        assert "competitive pricing" in rec.recommendation_reason.lower()  # With 95% price competitiveness

    @pytest.mark.asyncio
    async def test_calculate_price_competitiveness(self, engine, mock_db):
        """Test price competitiveness calculation."""
        # Create analysis with price data
        analysis = SearchResultAnalysis(
            id=str(uuid4()),
            search_id=str(uuid4()),
            total_results=10,
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"),
            avg_price=Decimal("35.00"),
        )

        # Test best price (lowest)
        seller_results = [
            SearchResult(id=str(uuid4()), item_price=Decimal("22.00")),
            SearchResult(id=str(uuid4()), item_price=Decimal("25.00")),
        ]
        score = await engine._calculate_price_competitiveness(mock_db, seller_results, analysis)
        assert score >= Decimal("80.0")  # Should be competitive

        # Test average price
        seller_results = [SearchResult(id=str(uuid4()), item_price=Decimal("35.00"))]
        score = await engine._calculate_price_competitiveness(mock_db, seller_results, analysis)
        assert Decimal("40.0") <= score <= Decimal("70.0")

        # Test high price
        seller_results = [SearchResult(id=str(uuid4()), item_price=Decimal("48.00"))]
        score = await engine._calculate_price_competitiveness(mock_db, seller_results, analysis)
        assert score <= Decimal("40.0")  # Should be uncompetitive
