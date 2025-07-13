"""Tests for search analysis API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    async def authenticated_client(self, async_client: AsyncClient):
        """Create authenticated client with mock user."""
        with patch("src.api.v1.endpoints.auth.get_current_user") as mock_get_user:
            mock_user = User(id=str(uuid4()), email="test@example.com", hashed_password="hashed", is_active=True)
            mock_get_user.return_value = mock_user
            yield async_client, mock_user

    @pytest.fixture
    def sample_search(self):
        """Create sample saved search."""
        return SavedSearch(
            id=str(uuid4()),
            user_id=str(uuid4()),
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
            id=str(uuid4()),
            search_id=sample_search.id,
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
    def sample_seller(self):
        """Create sample seller."""
        return Seller(
            id=str(uuid4()),
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller123",
            seller_name="Test Seller",
            location="Los Angeles, CA",
            country_code="US",
            feedback_score=Decimal("98.5"),
            total_feedback_count=1500,
            positive_feedback_percentage=Decimal("99.2"),
            ships_internationally=True,
        )

    @pytest.fixture
    def sample_recommendations(self, sample_analysis, sample_seller):
        """Create sample recommendations."""
        return [
            DealRecommendation(
                id=str(uuid4()),
                analysis_id=sample_analysis.id,
                seller_id=sample_seller.id,
                recommendation_type=RecommendationType.BEST_PRICE,
                deal_score=DealScore.EXCELLENT,
                score_value=Decimal("95.0"),
                total_items=3,
                wantlist_items=2,
                total_value=Decimal("75.00"),
                estimated_shipping=Decimal("15.00"),
                total_cost=Decimal("90.00"),
                potential_savings=Decimal("20.00"),
                title="Best Price Deal",
                description="Great deal on vinyl records",
                recommendation_reason="Competitive pricing with excellent seller reputation",
                item_ids=["item1", "item2", "item3"],
            ),
            DealRecommendation(
                id=str(uuid4()),
                analysis_id=sample_analysis.id,
                seller_id=sample_seller.id,
                recommendation_type=RecommendationType.MULTI_ITEM_DEAL,
                deal_score=DealScore.VERY_GOOD,
                score_value=Decimal("88.0"),
                total_items=5,
                wantlist_items=3,
                total_value=Decimal("125.00"),
                estimated_shipping=Decimal("15.00"),
                total_cost=Decimal("140.00"),
                potential_savings=Decimal("45.00"),
                title="Multi-Item Deal",
                description="Save on shipping with multiple items",
                recommendation_reason="Excellent savings on shipping costs",
                item_ids=["item1", "item2", "item3", "item4", "item5"],
            ),
        ]

    @pytest.fixture
    def sample_seller_analyses(self, sample_analysis, sample_seller):
        """Create sample seller analyses."""
        return [
            SellerAnalysis(
                id=str(uuid4()),
                search_analysis_id=sample_analysis.id,
                seller_id=sample_seller.id,
                total_items=5,
                wantlist_items=3,
                collection_duplicates=1,
                total_value=Decimal("125.00"),
                avg_item_price=Decimal("25.00"),
                estimated_shipping=Decimal("15.00"),
                price_competitiveness=Decimal("85.0"),
                inventory_depth_score=Decimal("90.0"),
                seller_reputation_score=Decimal("95.0"),
                location_preference_score=Decimal("100.0"),
                overall_score=Decimal("88.0"),
                recommendation_rank=1,
            )
        ]

    @pytest.mark.asyncio
    async def test_get_search_analysis_success(
        self,
        authenticated_client,
        sample_search,
        sample_analysis,
        sample_recommendations,
        sample_seller_analyses,
        sample_seller,
    ):
        """Test successful retrieval of search analysis."""
        client, mock_user = authenticated_client

        # Update search to belong to mock user
        sample_search.user_id = mock_user.id

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock database queries
            # Search query
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = sample_search

            # Analysis query
            analysis_result = MagicMock()
            analysis_result.scalar_one_or_none.return_value = sample_analysis

            # Recommendations query
            rec_result = MagicMock()
            rec_result.scalars.return_value.all.return_value = sample_recommendations

            # Seller analyses query
            seller_analysis_result = MagicMock()
            seller_analysis_result.scalars.return_value.all.return_value = sample_seller_analyses

            # Seller lookup queries
            seller_result = MagicMock()
            seller_result.scalar_one_or_none.return_value = sample_seller

            mock_db.execute.side_effect = [
                search_result,  # Search lookup
                analysis_result,  # Analysis lookup
                rec_result,  # Recommendations lookup
                seller_analysis_result,  # Seller analyses lookup
                seller_result,  # Seller lookup for first recommendation
                seller_result,  # Seller lookup for second recommendation
                seller_result,  # Seller lookup for seller analysis
            ]

            # Make request
            response = await client.get(f"/api/v1/search-analysis/search/{sample_search.id}/analysis")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify response structure
            assert data["search_id"] == sample_search.id
            assert data["analysis_completed"] is True
            assert "analysis" in data
            assert "recommendations" in data
            assert "seller_analyses" in data

            # Verify analysis data
            analysis_data = data["analysis"]
            assert analysis_data["total_results"] == 50
            assert analysis_data["total_sellers"] == 10
            assert analysis_data["min_price"] == 15.0
            assert analysis_data["max_price"] == 80.0
            assert analysis_data["avg_price"] == 35.0

            # Verify recommendations
            assert len(data["recommendations"]) == 2
            rec1 = data["recommendations"][0]
            assert rec1["type"] == "BEST_PRICE"
            assert rec1["deal_score"] == "EXCELLENT"
            assert rec1["total_items"] == 3
            assert rec1["wantlist_items"] == 2
            assert rec1["total_value"] == 75.0

            # Verify seller analyses
            assert len(data["seller_analyses"]) == 1
            seller_analysis = data["seller_analyses"][0]
            assert seller_analysis["rank"] == 1
            assert seller_analysis["total_items"] == 5
            assert seller_analysis["overall_score"] == 88.0

    @pytest.mark.asyncio
    async def test_get_search_analysis_not_found(self, authenticated_client):
        """Test search analysis for non-existent search."""
        client, mock_user = authenticated_client

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock search not found
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = search_result

            # Make request
            fake_search_id = str(uuid4())
            response = await client.get(f"/api/v1/search-analysis/search/{fake_search_id}/analysis")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Search not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_search_analysis_no_analysis(self, authenticated_client, sample_search):
        """Test search analysis when analysis not yet completed."""
        client, mock_user = authenticated_client
        sample_search.user_id = mock_user.id

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock search found but analysis not found
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = sample_search

            analysis_result = MagicMock()
            analysis_result.scalar_one_or_none.return_value = None

            mock_db.execute.side_effect = [search_result, analysis_result]

            # Make request
            response = await client.get(f"/api/v1/search-analysis/search/{sample_search.id}/analysis")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["analysis_completed"] is False
            assert "not yet completed" in data["message"]

    @pytest.mark.asyncio
    async def test_get_multi_item_deals_success(
        self, authenticated_client, sample_search, sample_analysis, sample_recommendations, sample_seller
    ):
        """Test successful retrieval of multi-item deals."""
        client, mock_user = authenticated_client
        sample_search.user_id = mock_user.id

        # Filter to only multi-item recommendations
        multi_item_recs = [
            rec for rec in sample_recommendations if rec.recommendation_type == RecommendationType.MULTI_ITEM_DEAL
        ]

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock database queries
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = sample_search

            analysis_result = MagicMock()
            analysis_result.scalar_one_or_none.return_value = sample_analysis

            rec_result = MagicMock()
            rec_result.scalars.return_value.all.return_value = multi_item_recs

            seller_result = MagicMock()
            seller_result.scalar_one_or_none.return_value = sample_seller

            mock_db.execute.side_effect = [search_result, analysis_result, rec_result, seller_result]

            # Make request
            response = await client.get(f"/api/v1/search-analysis/search/{sample_search.id}/multi-item-deals")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["search_id"] == sample_search.id
            assert "multi_item_deals" in data
            assert len(data["multi_item_deals"]) == 1

            deal = data["multi_item_deals"][0]
            assert deal["total_items"] == 5
            assert deal["wantlist_items"] == 3
            assert deal["deal_score"] == "VERY_GOOD"
            assert deal["potential_savings"] == 45.0

    @pytest.mark.asyncio
    async def test_get_price_comparison_success(self, authenticated_client, sample_search, sample_seller):
        """Test successful retrieval of price comparison data."""
        client, mock_user = authenticated_client
        sample_search.user_id = mock_user.id

        # Create sample search results and item match
        item_match = ItemMatch(
            id=str(uuid4()),
            canonical_title="Abbey Road",
            canonical_artist="The Beatles",
            canonical_year=1969,
            match_fingerprint="test-fingerprint",
            total_matches=2,
        )

        search_results = [
            SearchResult(
                id=str(uuid4()),
                search_id=sample_search.id,
                platform=SearchPlatform.DISCOGS,
                item_id="item1",
                seller_id=sample_seller.id,
                item_match_id=item_match.id,
                item_price=Decimal("25.00"),
                item_condition="VG+",
                item_data={"title": "Abbey Road", "artist": "The Beatles", "year": 1969},
                is_in_wantlist=True,
                is_in_collection=False,
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=sample_search.id,
                platform=SearchPlatform.EBAY,
                item_id="item2",
                seller_id=sample_seller.id,
                item_match_id=item_match.id,
                item_price=Decimal("30.00"),
                item_condition="NM",
                item_data={"title": "Abbey Road Remastered", "artist": "Beatles", "year": 2019},
                is_in_wantlist=True,
                is_in_collection=False,
            ),
        ]

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock database queries
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = sample_search

            # Mock search results query with joins
            results_query = MagicMock()
            results_query.all.return_value = [
                (search_results[0], item_match, sample_seller),
                (search_results[1], item_match, sample_seller),
            ]

            mock_db.execute.side_effect = [search_result, results_query]

            # Make request
            response = await client.get(f"/api/v1/search-analysis/search/{sample_search.id}/price-comparison")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["search_id"] == sample_search.id
            assert "price_comparisons" in data
            assert len(data["price_comparisons"]) == 1

            comparison = data["price_comparisons"][0]
            assert comparison["item_match"]["canonical_title"] == "Abbey Road"
            assert comparison["item_match"]["canonical_artist"] == "The Beatles"
            assert comparison["item_match"]["total_matches"] == 2
            assert len(comparison["listings"]) == 2

            # Verify listings are sorted by price
            listings = comparison["listings"]
            assert listings[0]["price"] == 25.0
            assert listings[1]["price"] == 30.0
            assert listings[0]["platform"] == "DISCOGS"
            assert listings[1]["platform"] == "EBAY"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test that endpoints require authentication."""
        fake_search_id = str(uuid4())

        # Test analysis endpoint
        response = await async_client.get(f"/api/v1/search-analysis/search/{fake_search_id}/analysis")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test multi-item deals endpoint
        response = await async_client.get(f"/api/v1/search-analysis/search/{fake_search_id}/multi-item-deals")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test price comparison endpoint
        response = await async_client.get(f"/api/v1/search-analysis/search/{fake_search_id}/price-comparison")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_access_other_user_search(self, authenticated_client, sample_search):
        """Test that users cannot access other users' searches."""
        client, mock_user = authenticated_client

        # Search belongs to different user
        sample_search.user_id = str(uuid4())  # Different from mock_user.id

        with patch("src.core.database.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value.__aenter__.return_value = mock_db

            # Mock search found but belongs to different user
            search_result = MagicMock()
            search_result.scalar_one_or_none.return_value = None  # Will not find search for this user
            mock_db.execute.return_value = search_result

            # Make request
            response = await client.get(f"/api/v1/search-analysis/search/{sample_search.id}/analysis")

            assert response.status_code == status.HTTP_404_NOT_FOUND
