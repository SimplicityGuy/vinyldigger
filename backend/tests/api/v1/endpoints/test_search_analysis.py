"""Tests for search analysis API endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.main import app
from src.models.item_match import ItemMatch
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import (
    DealRecommendation,
    DealScore,
    RecommendationType,
    SearchResultAnalysis,
    SellerAnalysis,
)
from src.models.seller import Seller
from src.models.user import User


class TestSearchAnalysisEndpoints:
    """Test suite for search analysis API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        return User(
            id=uuid4(),  # Use UUID object, not string
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )

    @pytest.fixture
    def authenticated_client(self, client: AsyncClient, mock_user):
        """Create authenticated client with mock user."""

        async def mock_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = mock_get_current_user
        yield client
        app.dependency_overrides.pop(get_current_user, None)

    @pytest.fixture
    def sample_search(self, mock_user):
        """Create sample saved search."""
        return SavedSearch(
            id=uuid4(),  # Use UUID object
            user_id=mock_user.id,
            name="Test Search",
            query="vinyl records",
            platform=SearchPlatform.BOTH,
            filters={},
            check_interval_hours=24,
            is_active=True,
        )

    @pytest.fixture
    def sample_analysis(self, sample_search):
        """Create sample search analysis."""
        return SearchResultAnalysis(
            id=uuid4(),  # Use UUID object
            search_id=sample_search.id,
            total_results=10,
            total_sellers=3,
            multi_item_sellers=1,
            min_price=Decimal("20.00"),
            max_price=Decimal("50.00"),
            avg_price=Decimal("30.00"),
            wantlist_matches=5,
            collection_duplicates=2,
            new_discoveries=3,
        )

    @pytest.fixture
    def sample_seller(self):
        """Create sample seller."""
        return Seller(
            id=uuid4(),  # Use UUID object
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller123",
            seller_name="Test Seller",
            location="Los Angeles, CA",
            country_code="US",
            feedback_score=Decimal("98.5"),
        )

    @pytest.mark.asyncio
    async def test_get_search_analysis_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_search, sample_analysis, sample_seller
    ):
        """Test successful retrieval of search analysis."""
        # Add test data to database
        db_session.add(sample_search)
        db_session.add(sample_analysis)
        db_session.add(sample_seller)
        await db_session.commit()

        # Create seller analysis
        seller_analysis = SellerAnalysis(
            id=uuid4(),
            search_analysis_id=sample_analysis.id,
            seller_id=sample_seller.id,
            total_items=3,
            wantlist_items=2,
            total_value=Decimal("90.00"),
            avg_item_price=Decimal("30.00"),
            estimated_shipping=Decimal("15.00"),
            overall_score=Decimal("85.0"),
            recommendation_rank=1,
        )
        db_session.add(seller_analysis)

        # Create recommendation
        recommendation = DealRecommendation(
            id=uuid4(),
            analysis_id=sample_analysis.id,
            seller_id=sample_seller.id,
            recommendation_type=RecommendationType.MULTI_ITEM_DEAL,
            deal_score=DealScore.EXCELLENT,
            score_value=Decimal("90.0"),
            total_items=3,
            wantlist_items=2,
            total_value=Decimal("90.00"),
            estimated_shipping=Decimal("15.00"),
            total_cost=Decimal("105.00"),
            title="Great Multi-Item Deal",
            description="Save on shipping",
            recommendation_reason="Buy 3 items together",
            item_ids=[str(uuid4()), str(uuid4()), str(uuid4())],
        )
        db_session.add(recommendation)
        await db_session.commit()

        # Test the endpoint
        response = await authenticated_client.get(f"/api/v1/analysis/search/{sample_search.id}/analysis")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_id"] == str(sample_search.id)
        assert data["analysis_completed"] is True
        assert "analysis" in data
        assert "recommendations" in data
        assert "seller_analyses" in data
        assert len(data["recommendations"]) == 1
        assert len(data["seller_analyses"]) == 1

    @pytest.mark.asyncio
    async def test_get_search_analysis_not_found(self, authenticated_client: AsyncClient):
        """Test analysis endpoint with non-existent search."""
        non_existent_id = uuid4()
        response = await authenticated_client.get(f"/api/v1/analysis/search/{non_existent_id}/analysis")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Search not found"

    @pytest.mark.asyncio
    async def test_get_search_analysis_no_analysis(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_search
    ):
        """Test analysis endpoint when analysis hasn't been completed."""
        # Add only the search, no analysis
        db_session.add(sample_search)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/analysis/search/{sample_search.id}/analysis")

        # Debug output
        if response.status_code != status.HTTP_200_OK:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")
            print(f"Search ID: {sample_search.id}")
            print(f"User ID: {sample_search.user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_id"] == str(sample_search.id)
        assert data["analysis_completed"] is False
        assert data["message"] == "Analysis not yet completed for this search"

    @pytest.mark.asyncio
    async def test_get_multi_item_deals_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_search, sample_analysis, sample_seller
    ):
        """Test successful retrieval of multi-item deals."""
        # Add test data
        db_session.add(sample_search)
        db_session.add(sample_analysis)
        db_session.add(sample_seller)

        # Create multi-item recommendation
        recommendation = DealRecommendation(
            id=uuid4(),
            analysis_id=sample_analysis.id,
            seller_id=sample_seller.id,
            recommendation_type=RecommendationType.MULTI_ITEM_DEAL,
            deal_score=DealScore.EXCELLENT,
            score_value=Decimal("90.0"),
            total_items=3,
            wantlist_items=2,
            total_value=Decimal("90.00"),
            estimated_shipping=Decimal("15.00"),
            total_cost=Decimal("105.00"),
            potential_savings=Decimal("30.00"),
            title="Multi-Item Deal",
            description="Save on shipping",
            recommendation_reason="Buy together",
            item_ids=[str(uuid4()), str(uuid4())],
        )
        db_session.add(recommendation)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/analysis/search/{sample_search.id}/multi-item-deals")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_id"] == str(sample_search.id)
        assert len(data["multi_item_deals"]) == 1
        deal = data["multi_item_deals"][0]
        assert deal["total_items"] == 3
        assert deal["wantlist_items"] == 2
        assert deal["deal_score"] == "EXCELLENT"

    @pytest.mark.asyncio
    async def test_get_multi_item_deals_no_analysis(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_search
    ):
        """Test multi-item deals endpoint when analysis hasn't been completed."""
        # Add only the search, no analysis
        db_session.add(sample_search)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/analysis/search/{sample_search.id}/multi-item-deals")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_id"] == str(sample_search.id)
        assert data["multi_item_deals"] == []
        assert data["message"] == "Analysis not yet completed for this search"

    @pytest.mark.asyncio
    async def test_get_price_comparison_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, sample_search, sample_seller
    ):
        """Test successful price comparison retrieval."""
        # Add test data
        db_session.add(sample_search)
        db_session.add(sample_seller)

        # Create item match
        item_match = ItemMatch(
            id=uuid4(),
            canonical_title="Test Album",
            canonical_artist="Test Artist",
            match_fingerprint="testalbumtestartist",
            total_matches=2,
            avg_confidence_score=Decimal("85.0"),
        )
        db_session.add(item_match)

        # Create search results
        result1 = SearchResult(
            id=uuid4(),
            search_id=sample_search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="disc123",
            item_price=Decimal("25.00"),
            item_condition="VG+",
            seller_id=sample_seller.id,
            item_match_id=item_match.id,
            is_in_wantlist=True,
            is_in_collection=False,
            item_data={"title": "Test Album", "artist": "Test Artist"},
        )

        result2 = SearchResult(
            id=uuid4(),
            search_id=sample_search.id,
            platform=SearchPlatform.EBAY,
            item_id="ebay456",
            item_price=Decimal("30.00"),
            item_condition="NM",
            seller_id=sample_seller.id,
            item_match_id=item_match.id,
            is_in_wantlist=True,
            is_in_collection=False,
            item_data={"title": "Test Album", "artist": "Test Artist"},
        )

        db_session.add(result1)
        db_session.add(result2)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/analysis/search/{sample_search.id}/price-comparison")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_id"] == str(sample_search.id)
        assert len(data["price_comparisons"]) == 1
        comparison = data["price_comparisons"][0]
        assert comparison["item_match"]["canonical_title"] == "Test Album"
        assert len(comparison["listings"]) == 2
        # Should be sorted by price
        assert comparison["listings"][0]["price"] == 25.0
        assert comparison["listings"][1]["price"] == 30.0

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that endpoints require authentication."""
        search_id = uuid4()

        # Test all endpoints without authentication
        endpoints = [
            f"/api/v1/analysis/search/{search_id}/analysis",
            f"/api/v1/analysis/search/{search_id}/multi-item-deals",
            f"/api/v1/analysis/search/{search_id}/price-comparison",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_access_other_user_search(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test that users cannot access other users' searches."""
        # Create a search belonging to a different user
        other_user_search = SavedSearch(
            id=uuid4(),
            user_id=uuid4(),  # Different user ID
            name="Other User Search",
            query="test",
            platform=SearchPlatform.BOTH,
            filters={},
            check_interval_hours=24,
            is_active=True,
        )
        db_session.add(other_user_search)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/analysis/search/{other_user_search.id}/analysis")
        assert response.status_code == status.HTTP_404_NOT_FOUND
