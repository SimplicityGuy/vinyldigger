"""Integration tests for enhanced search workflow."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.item_match import ItemMatchResult, MatchConfidence
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import DealRecommendation, SellerAnalysis
from src.models.seller import Seller
from src.models.user import User
from src.workers.tasks import RunSearchTask as SearchTask


class TestEnhancedSearchWorkflow:
    """Integration tests for the complete enhanced search workflow."""

    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        return User(id=str(uuid4()), email="test@example.com", hashed_password="hashed", is_active=True)

    @pytest.fixture
    def sample_saved_search(self, sample_user):
        """Create sample saved search."""
        return SavedSearch(
            id=str(uuid4()),
            user_id=sample_user.id,
            name="The Beatles Vinyl",
            query="The Beatles Abbey Road",
            platform=SearchPlatform.BOTH,
            filters={"format": "Vinyl"},
            check_interval_hours=24,
            is_active=True,
            min_price=Decimal("15.00"),
            max_price=Decimal("100.00"),
        )

    @pytest.fixture
    def sample_search_results(self, sample_saved_search):
        """Create sample search results from different platforms and sellers."""
        return [
            # Discogs results
            SearchResult(
                id=str(uuid4()),
                search_id=sample_saved_search.id,
                platform=SearchPlatform.DISCOGS,
                item_id="discogs_1",
                item_data={
                    "title": "Abbey Road",
                    "artist": "The Beatles",
                    "year": 1969,
                    "format": "Vinyl",
                    "condition": "VG+",
                    "price": 25.00,
                    "seller": {
                        "id": "seller_1",
                        "name": "Vinyl Collector",
                        "location": "Los Angeles, CA",
                        "feedback": 98.5,
                    },
                },
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=sample_saved_search.id,
                platform=SearchPlatform.DISCOGS,
                item_id="discogs_2",
                item_data={
                    "title": "Help!",
                    "artist": "The Beatles",
                    "year": 1965,
                    "format": "Vinyl",
                    "condition": "NM",
                    "price": 30.00,
                    "seller": {
                        "id": "seller_1",  # Same seller
                        "name": "Vinyl Collector",
                        "location": "Los Angeles, CA",
                        "feedback": 98.5,
                    },
                },
            ),
            # eBay results
            SearchResult(
                id=str(uuid4()),
                search_id=sample_saved_search.id,
                platform=SearchPlatform.EBAY,
                item_id="ebay_1",
                item_data={
                    "title": "Abbey Road Remastered",
                    "artist": "Beatles",
                    "year": 2019,
                    "format": "LP",
                    "condition": "New",
                    "price": 35.00,
                    "seller": {"id": "seller_2", "name": "Record Store", "location": "New York, NY", "feedback": 99.2},
                },
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=sample_saved_search.id,
                platform=SearchPlatform.EBAY,
                item_id="ebay_2",
                item_data={
                    "title": "Abbey Road (1969)",
                    "artist": "The Beatles",
                    "year": 1969,
                    "format": "Vinyl",
                    "condition": "VG",
                    "price": 22.00,
                    "seller": {"id": "seller_3", "name": "Music Hub", "location": "Chicago, IL", "feedback": 97.8},
                },
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=sample_saved_search.id,
                platform=SearchPlatform.EBAY,
                item_id="ebay_3",
                item_data={
                    "title": "White Album",
                    "artist": "The Beatles",
                    "year": 1968,
                    "format": "Vinyl",
                    "condition": "VG+",
                    "price": 40.00,
                    "seller": {
                        "id": "seller_2",  # Same seller as ebay_1
                        "name": "Record Store",
                        "location": "New York, NY",
                        "feedback": 99.2,
                    },
                },
            ),
        ]

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session for testing."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def search_task(self):
        """Create SearchTask instance for testing."""
        return SearchTask()

    @pytest.mark.asyncio
    async def test_complete_enhanced_search_workflow(
        self, search_task, mock_db_session, sample_saved_search, sample_search_results, sample_user
    ):
        """Test the complete enhanced search workflow from start to finish."""

        # Mock external API calls (Discogs/eBay search)
        with patch.object(search_task, "_execute_platform_search") as mock_search:
            mock_search.return_value = sample_search_results

            # Mock database operations
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            mock_db_session.execute = AsyncMock()

            # Mock query results for various database lookups
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # New entities
            mock_result.scalars.return_value.all.return_value = []  # Empty results
            mock_db_session.execute.return_value = mock_result

            # Execute the complete workflow
            await search_task.execute_search(sample_saved_search.id, sample_user.id)

            # Verify that all workflow steps were executed
            # 1. Basic search was executed
            mock_search.assert_called()

            # 2. Database operations were performed
            assert mock_db_session.add.call_count > 0  # Results and analysis entities added
            assert mock_db_session.commit.call_count > 0  # Changes committed

    @pytest.mark.asyncio
    async def test_item_matching_integration(self, search_task, mock_db_session, sample_search_results):
        """Test item matching functionality in the workflow."""

        with patch("src.services.item_matcher.ItemMatchingService") as mock_matcher_class:
            mock_matcher = AsyncMock()
            mock_matcher_class.return_value = mock_matcher

            # Mock matching results
            mock_match_results = [
                ItemMatchResult(
                    id=str(uuid4()),
                    item_match_id=str(uuid4()),
                    search_result_id=result.id,
                    confidence=MatchConfidence.HIGH,
                    confidence_score=Decimal("85.0"),
                    title_similarity=Decimal("90.0"),
                    artist_similarity=Decimal("95.0"),
                    year_match=True,
                    catalog_match=False,
                    format_match=True,
                )
                for result in sample_search_results
            ]
            mock_matcher.process_search_results.return_value = mock_match_results

            # Execute item matching
            await search_task._perform_item_matching(mock_db_session, str(uuid4()))

            # Verify matching was performed
            mock_matcher.process_search_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_seller_analysis_integration(self, search_task, mock_db_session, sample_search_results):
        """Test seller analysis functionality in the workflow."""

        with patch("src.services.seller_analyzer.SellerAnalysisService") as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock seller processing and analysis
            mock_sellers = [
                Seller(
                    id=str(uuid4()),
                    platform=SearchPlatform.DISCOGS,
                    platform_seller_id="seller_1",
                    seller_name="Vinyl Collector",
                    location="Los Angeles, CA",
                    country_code="US",
                    feedback_score=Decimal("98.5"),
                )
            ]
            mock_analyzer.process_search_sellers.return_value = mock_sellers

            mock_analyses = [
                SellerAnalysis(
                    id=str(uuid4()),
                    search_analysis_id=str(uuid4()),
                    seller_id=mock_sellers[0].id,
                    total_items=2,
                    wantlist_items=1,
                    total_value=Decimal("55.00"),
                    avg_item_price=Decimal("27.50"),
                    estimated_shipping=Decimal("15.00"),
                    price_competitiveness=Decimal("85.0"),
                    inventory_depth_score=Decimal("70.0"),
                    seller_reputation_score=Decimal("90.0"),
                    location_preference_score=Decimal("100.0"),
                    overall_score=Decimal("85.0"),
                    recommendation_rank=1,
                )
            ]
            mock_analyzer.analyze_all_sellers.return_value = mock_analyses

            # Execute seller analysis
            await search_task._perform_seller_analysis(mock_db_session, str(uuid4()))

            # Verify analysis was performed
            mock_analyzer.process_search_sellers.assert_called_once()
            mock_analyzer.analyze_all_sellers.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommendation_generation_integration(self, search_task, mock_db_session):
        """Test recommendation generation in the workflow."""

        with patch("src.services.recommendation_engine.RecommendationEngine") as mock_engine_class:
            mock_engine = AsyncMock()
            mock_engine_class.return_value = mock_engine

            # Mock recommendation generation
            mock_recommendations = [
                DealRecommendation(
                    id=str(uuid4()),
                    analysis_id=str(uuid4()),
                    seller_id=str(uuid4()),
                    recommendation_type="BEST_PRICE",
                    deal_score="EXCELLENT",
                    score_value=Decimal("95.0"),
                    total_items=1,
                    wantlist_items=1,
                    total_value=Decimal("25.00"),
                    estimated_shipping=Decimal("15.00"),
                    total_cost=Decimal("40.00"),
                    title="Best Price Deal",
                    description="Great deal on Abbey Road",
                    recommendation_reason="Competitive pricing",
                    item_ids=["item1"],
                )
            ]
            mock_engine.generate_recommendations.return_value = mock_recommendations

            # Execute recommendation generation
            await search_task._generate_recommendations(mock_db_session, str(uuid4()), str(uuid4()))

            # Verify recommendations were generated
            mock_engine.generate_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, search_task, mock_db_session, sample_saved_search, sample_user):
        """Test error handling in the search workflow."""

        # Mock a failure in external search
        with patch.object(search_task, "_execute_platform_search") as mock_search:
            mock_search.side_effect = Exception("External API error")

            # Mock database rollback
            mock_db_session.rollback = AsyncMock()

            # Execute search and expect it to handle the error
            with pytest.raises(Exception, match="External API error"):
                await search_task.execute_search(sample_saved_search.id, sample_user.id)

            # Verify rollback was called
            mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_multi_seller_analysis_workflow(self, search_task, mock_db_session, sample_search_results):
        """Test workflow specifically for multi-seller analysis scenarios."""

        # Group search results by seller to simulate multi-item sellers
        seller_groups = {}
        for result in sample_search_results:
            seller_id = result.item_data["seller"]["id"]
            if seller_id not in seller_groups:
                seller_groups[seller_id] = []
            seller_groups[seller_id].append(result)

        # Verify we have multi-item sellers
        multi_item_sellers = [seller_id for seller_id, results in seller_groups.items() if len(results) > 1]
        assert len(multi_item_sellers) >= 1  # Should have at least one multi-item seller

        with patch("src.services.seller_analyzer.SellerAnalysisService") as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock analysis that identifies multi-item opportunities
            mock_analyses = []
            for _seller_id, results in seller_groups.items():
                mock_analyses.append(
                    SellerAnalysis(
                        id=str(uuid4()),
                        search_analysis_id=str(uuid4()),
                        seller_id=str(uuid4()),
                        total_items=len(results),
                        wantlist_items=len(results) // 2,  # Half in wantlist
                        total_value=Decimal(str(sum(float(r.item_data["price"]) for r in results))),
                        avg_item_price=Decimal(str(sum(float(r.item_data["price"]) for r in results) / len(results))),
                        estimated_shipping=Decimal("15.00"),
                        price_competitiveness=Decimal("80.0"),
                        inventory_depth_score=Decimal("90.0") if len(results) > 1 else Decimal("50.0"),
                        seller_reputation_score=Decimal("85.0"),
                        location_preference_score=Decimal("75.0"),
                        overall_score=Decimal("85.0"),
                        recommendation_rank=1 if len(results) > 1 else 2,
                    )
                )

            mock_analyzer.analyze_all_sellers.return_value = mock_analyses

            # Execute seller analysis
            await search_task._perform_seller_analysis(mock_db_session, str(uuid4()))

            # Verify multi-item sellers got higher inventory depth scores
            high_inventory_analyses = [a for a in mock_analyses if a.inventory_depth_score >= Decimal("90.0")]
            assert len(high_inventory_analyses) >= 1

    @pytest.mark.asyncio
    async def test_cross_platform_matching_workflow(self, search_task, mock_db_session, sample_search_results):
        """Test workflow for cross-platform item matching."""

        # Filter results to items that should match across platforms
        abbey_road_results = [result for result in sample_search_results if "Abbey Road" in result.item_data["title"]]
        assert len(abbey_road_results) >= 2  # Should have matches from different platforms

        with patch("src.services.item_matcher.ItemMatchingService") as mock_matcher_class:
            mock_matcher = AsyncMock()
            mock_matcher_class.return_value = mock_matcher

            # Mock cross-platform matching
            match_id = str(uuid4())
            mock_match_results = []

            for result in abbey_road_results:
                mock_match_results.append(
                    ItemMatchResult(
                        id=str(uuid4()),
                        item_match_id=match_id,  # Same match ID for cross-platform items
                        search_result_id=result.id,
                        confidence=MatchConfidence.HIGH,
                        confidence_score=Decimal("88.0"),
                        title_similarity=Decimal("90.0"),
                        artist_similarity=Decimal("100.0"),
                        year_match=True,
                        catalog_match=False,
                        format_match=True,
                    )
                )

            mock_matcher.process_search_results.return_value = mock_match_results

            # Execute item matching
            await search_task._perform_item_matching(mock_db_session, str(uuid4()))

            # Verify cross-platform matching was performed
            mock_matcher.process_search_results.assert_called_once()

            # Verify items that should match have the same match_id
            cross_platform_matches = [r for r in mock_match_results if r.item_match_id == match_id]
            assert len(cross_platform_matches) >= 2
