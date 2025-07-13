"""Tests for RecommendationEngine."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SearchPlatform
from src.models.search_analysis import (
    DealRecommendation,
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
    def sample_analysis(self):
        """Create sample search analysis."""
        return SearchResultAnalysis(
            id="analysis-1",
            search_id="search-1",
            total_results=50,
            total_sellers=10,
            multi_item_sellers=3,
            min_price=Decimal("15.00"),
            max_price=Decimal("80.00"),
            avg_price=Decimal("35.00"),
            wantlist_matches=25,
            collection_duplicates=5,
            new_discoveries=20,
        )

    @pytest.fixture
    def sample_sellers(self):
        """Create sample sellers for testing."""
        return [
            Seller(
                id=f"seller-{i}",
                platform=SearchPlatform.DISCOGS,
                platform_seller_id=f"seller{i}",
                seller_name=f"Seller {i}",
                location="Los Angeles, CA",
                country_code="US",
                feedback_score=Decimal(f"{95 + i}.0"),
                total_feedback_count=1000 + i * 100,
                positive_feedback_percentage=Decimal(f"{98 + i * 0.1}.0"),
                ships_internationally=True,
            )
            for i in range(3)
        ]

    @pytest.fixture
    def sample_seller_analyses(self, sample_analysis, sample_sellers):
        """Create sample seller analyses."""
        return [
            SellerAnalysis(
                id=f"seller-analysis-{i}",
                search_analysis_id=sample_analysis.id,
                seller_id=sample_sellers[i].id,
                total_items=5 + i * 2,
                wantlist_items=3 + i,
                collection_duplicates=1,
                total_value=Decimal(f"{100 + i * 50}.00"),
                avg_item_price=Decimal(f"{20 + i * 5}.00"),
                estimated_shipping=Decimal("15.00"),
                price_competitiveness=Decimal(f"{80 - i * 10}.0"),
                inventory_depth_score=Decimal(f"{70 + i * 10}.0"),
                seller_reputation_score=Decimal(f"{90 + i * 2}.0"),
                location_preference_score=Decimal("100.0"),
                overall_score=Decimal(f"{85 - i * 5}.0"),
                recommendation_rank=i + 1,
            )
            for i in range(3)
        ]

    def test_calculate_deal_score_excellent(self, engine):
        """Test deal score calculation for excellent deals."""
        score = engine.calculate_deal_score(Decimal("95.0"))
        assert score == DealScore.EXCELLENT

    def test_calculate_deal_score_very_good(self, engine):
        """Test deal score calculation for very good deals."""
        score = engine.calculate_deal_score(Decimal("82.0"))
        assert score == DealScore.VERY_GOOD

    def test_calculate_deal_score_good(self, engine):
        """Test deal score calculation for good deals."""
        score = engine.calculate_deal_score(Decimal("72.0"))
        assert score == DealScore.GOOD

    def test_calculate_deal_score_fair(self, engine):
        """Test deal score calculation for fair deals."""
        score = engine.calculate_deal_score(Decimal("62.0"))
        assert score == DealScore.FAIR

    def test_calculate_deal_score_poor(self, engine):
        """Test deal score calculation for poor deals."""
        score = engine.calculate_deal_score(Decimal("45.0"))
        assert score == DealScore.POOR

    def test_calculate_savings_vs_individual_purchases(self, engine):
        """Test savings calculation for multi-item purchases."""
        # Test shipping savings
        savings = engine.calculate_savings_vs_individual_purchases(total_items=3, estimated_shipping=Decimal("15.00"))
        # Should save 2 additional shipping costs (3-1) * 15.00 = 30.00
        assert savings == Decimal("30.00")

        # Single item should have no savings
        savings = engine.calculate_savings_vs_individual_purchases(total_items=1, estimated_shipping=Decimal("15.00"))
        assert savings == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_create_best_price_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test creating best price recommendations."""
        # Mock database query for top sellers by price competitiveness
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_seller_analyses[:2]
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]
        mock_db.execute.side_effect = [mock_result, mock_seller_result, mock_seller_result]

        # Test creating recommendations
        recommendations = await engine.create_best_price_recommendations(mock_db, sample_analysis)

        assert len(recommendations) <= 2
        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.recommendation_type == RecommendationType.BEST_PRICE
            assert "competitive price" in rec.recommendation_reason.lower()

    @pytest.mark.asyncio
    async def test_create_multi_item_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test creating multi-item deal recommendations."""
        # Filter to multi-item sellers
        multi_item_analyses = [sa for sa in sample_seller_analyses if sa.total_items >= 3]

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = multi_item_analyses
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]
        mock_db.execute.side_effect = [mock_result] + [mock_seller_result] * len(multi_item_analyses)

        # Test creating recommendations
        recommendations = await engine.create_multi_item_recommendations(mock_db, sample_analysis)

        assert len(recommendations) >= 1
        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.recommendation_type == RecommendationType.MULTI_ITEM_DEAL
            assert rec.total_items >= 3
            assert "shipping" in rec.recommendation_reason.lower()

    @pytest.mark.asyncio
    async def test_create_condition_value_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test creating condition value recommendations."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_seller_analyses
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]
        mock_db.execute.side_effect = [mock_result] + [mock_seller_result] * len(sample_seller_analyses)

        # Test creating recommendations
        recommendations = await engine.create_condition_value_recommendations(mock_db, sample_analysis)

        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.recommendation_type == RecommendationType.CONDITION_VALUE
            assert "condition" in rec.recommendation_reason.lower()

    @pytest.mark.asyncio
    async def test_create_location_preference_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test creating location preference recommendations."""
        # Mock database query for local sellers
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_seller_analyses[:1]
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]
        mock_db.execute.side_effect = [mock_result, mock_seller_result]

        # Test creating recommendations
        recommendations = await engine.create_location_preference_recommendations(mock_db, sample_analysis, "US")

        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.recommendation_type == RecommendationType.LOCATION_PREFERENCE
            assert "local" in rec.recommendation_reason.lower() or "shipping" in rec.recommendation_reason.lower()

    @pytest.mark.asyncio
    async def test_create_high_feedback_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test creating high feedback recommendations."""
        # Mock database query for high feedback sellers
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_seller_analyses[:1]
        mock_db.execute.return_value = mock_result

        # Mock seller lookup
        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]
        mock_db.execute.side_effect = [mock_result, mock_seller_result]

        # Test creating recommendations
        recommendations = await engine.create_high_feedback_recommendations(mock_db, sample_analysis)

        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.recommendation_type == RecommendationType.HIGH_FEEDBACK
            assert "feedback" in rec.recommendation_reason.lower() or "reputation" in rec.recommendation_reason.lower()

    @pytest.mark.asyncio
    async def test_generate_all_recommendations(
        self, engine, mock_db, sample_analysis, sample_sellers, sample_seller_analyses
    ):
        """Test generating all types of recommendations."""
        # Mock various database queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_seller_analyses

        mock_seller_result = MagicMock()
        mock_seller_result.scalar_one_or_none.return_value = sample_sellers[0]

        # Mock multiple queries (one for each recommendation type)
        mock_db.execute.side_effect = [mock_result, mock_seller_result] * 10  # Enough for all types

        # Test generating all recommendations
        recommendations = await engine.generate_recommendations(mock_db, sample_analysis, "user-1", "US")

        # Should have multiple types of recommendations
        assert len(recommendations) > 0

        # Check that we have different types
        recommendation_types = {rec.recommendation_type for rec in recommendations}
        assert len(recommendation_types) > 1  # Multiple types generated

        # All should be properly formatted
        for rec in recommendations:
            assert isinstance(rec, DealRecommendation)
            assert rec.analysis_id == sample_analysis.id
            assert rec.title
            assert rec.description
            assert rec.recommendation_reason
            assert rec.score_value >= Decimal("0.0")
            assert rec.total_value > Decimal("0.0")

    def test_create_recommendation_title_best_price(self, engine):
        """Test recommendation title creation for best price."""
        title = engine.create_recommendation_title(RecommendationType.BEST_PRICE, "Test Seller", 3, Decimal("45.00"))
        assert "Best Price" in title
        assert "Test Seller" in title
        assert "3 items" in title
        assert "$45.00" in title

    def test_create_recommendation_title_multi_item(self, engine):
        """Test recommendation title creation for multi-item deal."""
        title = engine.create_recommendation_title(
            RecommendationType.MULTI_ITEM_DEAL, "Vinyl Store", 5, Decimal("125.00")
        )
        assert "Multi-Item Deal" in title
        assert "Vinyl Store" in title
        assert "5 items" in title
        assert "$125.00" in title

    def test_create_recommendation_description(self, engine, sample_sellers, sample_seller_analyses):
        """Test recommendation description creation."""
        seller_analysis = sample_seller_analyses[0]
        seller = sample_sellers[0]

        description = engine.create_recommendation_description(RecommendationType.BEST_PRICE, seller, seller_analysis)

        assert seller.seller_name in description
        assert str(seller_analysis.total_items) in description
        assert "wantlist" in description.lower()
        assert "$" in description  # Should contain price info

    def test_format_recommendation_reason_best_price(self, engine):
        """Test formatting recommendation reason for best price."""
        reason = engine.format_recommendation_reason(
            RecommendationType.BEST_PRICE,
            price_competitiveness=Decimal("95.0"),
            inventory_depth=Decimal("70.0"),
            seller_reputation=Decimal("85.0"),
            wantlist_items=3,
            total_items=5,
            potential_savings=Decimal("20.00"),
        )

        assert "competitive pric" in reason.lower()
        assert "95%" in reason

    def test_format_recommendation_reason_multi_item(self, engine):
        """Test formatting recommendation reason for multi-item deal."""
        reason = engine.format_recommendation_reason(
            RecommendationType.MULTI_ITEM_DEAL,
            price_competitiveness=Decimal("80.0"),
            inventory_depth=Decimal("90.0"),
            seller_reputation=Decimal("85.0"),
            wantlist_items=4,
            total_items=6,
            potential_savings=Decimal("30.00"),
        )

        assert "multiple items" in reason.lower()
        assert "shipping" in reason.lower()
        assert "$30.00" in reason
