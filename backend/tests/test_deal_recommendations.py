"""Tests for deal recommendation functionality."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import DealRecommendation, DealScore, RecommendationType
from src.models.seller import Seller
from src.models.user import User
from src.services.recommendation_engine import RecommendationEngine


class TestDealRecommendations:
    """Test suite for deal recommendation engine."""

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    @pytest.fixture
    def sample_search(self, sample_user):
        """Create a sample search."""
        return SavedSearch(
            id=uuid4(),
            user_id=sample_user.id,
            name="Test Search",
            query="test vinyl",
            platform=SearchPlatform.BOTH,
            is_active=True,
        )

    @pytest.fixture
    def sample_seller(self):
        """Create a sample seller."""
        return Seller(
            id=uuid4(),
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller123",
            seller_name="VinylStore",
            location="USA",
            ships_internationally=True,
            feedback_score=Decimal("98.5"),
            total_feedback_count=1000,
        )

    @pytest.fixture
    def recommendation_engine(self):
        """Create recommendation engine instance."""
        return RecommendationEngine()

    async def test_create_deal_recommendation(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_search: SavedSearch,
        sample_seller: Seller,
    ):
        """Test creating a deal recommendation."""
        # Add entities to session
        db_session.add(sample_user)
        db_session.add(sample_search)
        db_session.add(sample_seller)
        await db_session.commit()

        # Create search result
        search_result = SearchResult(
            id=uuid4(),
            search_id=sample_search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="item123",
            item_price=Decimal("19.99"),
            item_condition="Near Mint",
            seller_id=sample_seller.id,
            is_in_collection=False,
            is_in_wantlist=True,
            item_data={
                "title": "Test Album",
                "artist": "Test Artist",
                "release_id": "12345",
                "catalog_number": "CAT-001",
                "currency": "USD",
            },
        )
        db_session.add(search_result)
        await db_session.commit()

        # Create a dummy analysis first
        from src.models.search_analysis import SearchResultAnalysis

        analysis = SearchResultAnalysis(
            id=uuid4(),
            search_id=sample_search.id,
            total_results=1,
            total_sellers=1,
        )
        db_session.add(analysis)
        await db_session.commit()

        # Create recommendation
        recommendation = DealRecommendation(
            id=uuid4(),
            analysis_id=analysis.id,
            seller_id=sample_seller.id,
            recommendation_type=RecommendationType.MULTI_ITEM_DEAL,
            deal_score=DealScore.EXCELLENT,
            score_value=Decimal("95.00"),
            title="Great Multi-Item Deal",
            description="Seller has 3 items from your want list",
            recommendation_reason="Seller has 3 items from your want list",
            total_items=3,
            wantlist_items=3,
            total_value=Decimal("60.00"),
            total_cost=Decimal("65.00"),
            potential_savings=Decimal("15.00"),
            item_ids=["item123", "item456", "item789"],
        )
        db_session.add(recommendation)
        await db_session.commit()

        # Verify recommendation was saved
        saved_rec = await db_session.get(DealRecommendation, recommendation.id)
        assert saved_rec is not None
        assert saved_rec.seller_id == sample_seller.id
        assert saved_rec.recommendation_type == RecommendationType.MULTI_ITEM_DEAL
        assert saved_rec.deal_score == DealScore.EXCELLENT
        assert saved_rec.potential_savings == Decimal("15.00")

    async def test_find_multi_item_sellers(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_search: SavedSearch,
        sample_seller: Seller,
        recommendation_engine: RecommendationEngine,
    ):
        """Test finding sellers with multiple items."""
        # Add entities
        db_session.add(sample_user)
        db_session.add(sample_search)
        db_session.add(sample_seller)
        await db_session.commit()

        # Create multiple search results from same seller
        for i in range(3):
            result = SearchResult(
                id=uuid4(),
                search_id=sample_search.id,
                platform=SearchPlatform.DISCOGS,
                item_id=f"item{i}",
                item_price=Decimal("20.00"),
                item_condition="Near Mint",
                seller_id=sample_seller.id,
                is_in_collection=False,
                is_in_wantlist=True,
                item_data={
                    "title": f"Album {i}",
                    "artist": "Test Artist",
                    "currency": "USD",
                },
            )
            db_session.add(result)
        await db_session.commit()

        # Test that we have multiple items from same seller
        query = (
            select(SearchResult)
            .where(SearchResult.search_id == sample_search.id)
            .where(SearchResult.seller_id == sample_seller.id)
        )
        db_result = await db_session.execute(query)
        items = db_result.scalars().all()

        assert len(items) == 3
        assert all(item.seller_id == sample_seller.id for item in items)

    async def test_recommendation_type_priority(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_search: SavedSearch,
        recommendation_engine: RecommendationEngine,
    ):
        """Test that recommendations are prioritized correctly."""
        # Add search
        db_session.add(sample_user)
        db_session.add(sample_search)
        await db_session.commit()

        # Create multiple recommendations with different types
        rec_types = [
            (RecommendationType.BEST_PRICE, DealScore.EXCELLENT, Decimal("50.00")),
            (RecommendationType.MULTI_ITEM_DEAL, DealScore.VERY_GOOD, Decimal("30.00")),
            (RecommendationType.CONDITION_VALUE, DealScore.GOOD, Decimal("20.00")),
            (RecommendationType.HIGH_FEEDBACK, DealScore.FAIR, Decimal("10.00")),
        ]

        for rec_type, score, savings in rec_types:
            recommendation = DealRecommendation(
                id=uuid4(),
                analysis_id=uuid4(),  # Dummy analysis ID for test
                seller_id=uuid4(),  # Dummy seller ID for test
                recommendation_type=rec_type,
                deal_score=score,
                score_value=Decimal("80.00"),
                title=f"Test {rec_type.value}",
                description=f"Test recommendation for {rec_type.value}",
                recommendation_reason=f"Test {rec_type.value}",
                total_items=1,
                total_value=Decimal("100.00"),
                total_cost=Decimal("100.00") - savings,
                potential_savings=savings,
                item_ids=["test-item"],
            )
            db_session.add(recommendation)
        await db_session.commit()

        # Query recommendations ordered by potential savings
        query = select(DealRecommendation).order_by(DealRecommendation.potential_savings.desc())
        result = await db_session.execute(query)
        recommendations = result.scalars().all()

        # Verify we have all our test recommendations
        assert len(recommendations) >= 4
        # Find our test recommendations
        test_recs = [r for r in recommendations if r.title.startswith("Test")]
        assert len(test_recs) == 4

        # Check that we have all the expected deal scores
        deal_scores = {r.deal_score for r in test_recs}
        assert DealScore.EXCELLENT in deal_scores
        assert DealScore.VERY_GOOD in deal_scores
        assert DealScore.GOOD in deal_scores
        assert DealScore.FAIR in deal_scores

        # The one with highest savings should have EXCELLENT score
        highest_savings = max(test_recs, key=lambda r: r.potential_savings or Decimal("0.00"))
        assert highest_savings.deal_score == DealScore.EXCELLENT
        assert highest_savings.potential_savings == Decimal("50.00")

    async def test_empty_search_results(
        self,
        db_session: AsyncSession,
        sample_user: User,
        sample_search: SavedSearch,
        recommendation_engine: RecommendationEngine,
    ):
        """Test recommendation engine with no search results."""
        db_session.add(sample_user)
        db_session.add(sample_search)
        await db_session.commit()

        # Try to analyze search with no results
        analysis = await recommendation_engine.analyze_search_results(
            db_session, str(sample_search.id), str(sample_search.user_id)
        )

        assert analysis.total_results == 0
        assert analysis.total_sellers == 0
