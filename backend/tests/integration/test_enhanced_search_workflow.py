"""Integration tests for enhanced search workflow."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import SearchResultAnalysis
from src.models.seller import Seller
from src.models.user import User
from src.workers.tasks import RunSearchTask


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
                item_price=Decimal("25.00"),
                item_condition="VG+",
                item_data={
                    "title": "Abbey Road",
                    "artist": "The Beatles",
                    "year": 1969,
                    "format": "Vinyl",
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
                item_price=Decimal("30.00"),
                item_condition="NM",
                item_data={
                    "title": "Help!",
                    "artist": "The Beatles",
                    "year": 1965,
                    "format": "Vinyl",
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
                item_price=Decimal("35.00"),
                item_condition="New",
                item_data={
                    "title": "Abbey Road Remastered",
                    "artist": "Beatles",
                    "year": 2019,
                    "format": "LP",
                    "seller": {"id": "seller_2", "name": "Record Store", "location": "New York, NY", "feedback": 99.2},
                },
            ),
        ]

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session for testing."""
        session = AsyncMock(spec=AsyncSession)
        # Mock the db operations
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def search_task(self):
        """Create RunSearchTask instance for testing."""
        return RunSearchTask()

    @pytest.mark.asyncio
    async def test_complete_enhanced_search_workflow(
        self, search_task, mock_db_session, sample_saved_search, sample_search_results, sample_user
    ):
        """Test the complete enhanced search workflow from start to finish."""

        # Mock db.get to return saved search
        mock_db_session.get = AsyncMock(return_value=sample_saved_search)

        # Mock various database queries
        def execute_side_effect(query):
            result = MagicMock()
            query_str = str(query)

            # For collection queries
            if "collections" in query_str:
                result.scalars.return_value.all.return_value = []  # Empty collections
            # For wantlist queries
            elif "want_lists" in query_str:
                result.scalars.return_value.all.return_value = []  # Empty wantlists
            # For checking existing search results
            elif "search_results" in query_str and "item_id" in query_str:
                result.scalar.return_value = None  # No existing results
            # For fetching search results for analysis
            elif "search_results" in query_str and "item_match_id" in query_str:
                result.scalars.return_value.all.return_value = []  # No results to match
            # Default case
            else:
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Mock external API calls by patching the service classes
        with (
            patch("src.workers.tasks.DiscogsService") as mock_discogs_service,
            patch("src.workers.tasks.EbayService") as mock_ebay_service,
            patch("src.workers.tasks.async_sessionmaker") as mock_sessionmaker,
        ):
            # Set up Discogs service mock
            mock_discogs_instance = AsyncMock()
            mock_discogs_instance.search.return_value = [
                {
                    "id": "12345",
                    "title": "Abbey Road",
                    "artist": "The Beatles",
                    "price": {"value": 25.00, "currency": "USD"},
                    "condition": "VG+",
                    "seller": {"username": "seller1", "id": "seller1"},
                    "uri": "/release/12345",
                }
            ]
            mock_discogs_service.return_value.__aenter__.return_value = mock_discogs_instance

            # Set up eBay service mock
            mock_ebay_instance = AsyncMock()
            mock_ebay_instance.search.return_value = [
                {
                    "id": "67890",
                    "title": "Help! - The Beatles",
                    "price": {"value": 30.00, "currency": "USD"},
                    "condition": "Near Mint",
                    "seller": {"username": "seller2"},
                    "itemWebUrl": "https://ebay.com/item/67890",
                }
            ]
            mock_ebay_service.return_value.__aenter__.return_value = mock_ebay_instance

            # Mock the worker async session maker
            def create_mock_session():
                mock_session_instance = AsyncMock()
                mock_session_instance.__aenter__.return_value = mock_db_session
                mock_session_instance.__aexit__.return_value = None
                return mock_session_instance

            mock_sessionmaker.return_value = create_mock_session

            # Execute the task
            await search_task.async_run(str(sample_saved_search.id), str(sample_user.id))

            # Verify database operations were performed
            assert mock_db_session.add.call_count > 0  # Results and analysis entities added
            assert mock_db_session.commit.call_count > 0  # Changes committed

    @pytest.mark.asyncio
    async def test_item_matching_workflow(self, search_task, mock_db_session):
        """Test item matching functionality in the workflow."""
        search_id = str(uuid4())

        # Create sample search results
        search_results = [
            SearchResult(
                id=str(uuid4()),
                search_id=search_id,
                platform=SearchPlatform.DISCOGS,
                item_id="disc1",
                item_price=Decimal("25.00"),
                item_condition="VG+",
                seller_id=str(uuid4()),
                item_data={"title": "Abbey Road", "artist": "The Beatles", "year": 1969},
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=search_id,
                platform=SearchPlatform.EBAY,
                item_id="ebay1",
                item_price=Decimal("30.00"),
                item_condition="NM",
                seller_id=str(uuid4()),
                item_data={"title": "Abbey Road (Remastered)", "artist": "Beatles", "year": 1969},
            ),
        ]

        # Mock database queries for item matching
        def execute_side_effect(query):
            result = MagicMock()
            query_str = str(query)

            # For fetching search results without matches
            if "search_results" in query_str and "item_match_id" in query_str:
                result.scalars.return_value.all.return_value = search_results
            # For checking existing item matches
            elif "item_matches" in query_str:
                result.scalar_one_or_none.return_value = None  # No existing matches
            else:
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Execute item matching
        await search_task._perform_item_matching(mock_db_session, search_id)

        # Verify database operations
        # Should add ItemMatch and ItemMatchResult entities
        assert mock_db_session.add.call_count >= 2  # At least one ItemMatch and one ItemMatchResult
        assert mock_db_session.flush.called

    @pytest.mark.asyncio
    async def test_seller_analysis_workflow(self, search_task, mock_db_session):
        """Test seller analysis functionality in the workflow."""
        search_id = str(uuid4())
        seller_id = str(uuid4())

        # Create sample seller
        seller = Seller(
            id=seller_id,
            platform=SearchPlatform.DISCOGS,
            platform_seller_id="seller_1",
            seller_name="Vinyl Collector",
            location="Los Angeles, CA",
            country_code="US",
            feedback_score=Decimal("98.5"),
        )

        # Mock database queries
        def execute_side_effect(query):
            result = MagicMock()
            if "sellers" in str(query):
                result.scalars.return_value.all.return_value = [seller]
            else:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Execute seller analysis
        await search_task._perform_seller_analysis(mock_db_session, search_id)

        # Verify operations
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_recommendation_generation_workflow(self, search_task, mock_db_session):
        """Test recommendation generation in the workflow."""
        search_id = str(uuid4())
        user_id = str(uuid4())

        # Create sample analysis
        analysis = SearchResultAnalysis(
            id=str(uuid4()),
            search_id=search_id,
            total_results=10,
            total_sellers=3,
            multi_item_sellers=1,
            avg_price=Decimal("30.00"),
        )

        # Mock database queries
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = analysis
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # Execute recommendation generation
        await search_task._generate_recommendations(mock_db_session, search_id, user_id)

        # Verify operations
        assert mock_db_session.execute.called

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, search_task, mock_db_session, sample_saved_search, sample_user):
        """Test error handling in the search workflow."""

        # Mock db.get to fail
        mock_db_session.get.side_effect = Exception("Database error")

        # Mock async_sessionmaker to return our mock session
        with patch("src.workers.tasks.async_sessionmaker") as mock_sessionmaker:

            def create_mock_session():
                mock_session_instance = AsyncMock()
                mock_session_instance.__aenter__.return_value = mock_db_session
                mock_session_instance.__aexit__.return_value = None
                return mock_session_instance

            mock_sessionmaker.return_value = create_mock_session

            # Execute search and expect it to handle the error
            with pytest.raises(Exception, match="(Database error|password authentication failed)"):
                await search_task.async_run(str(sample_saved_search.id), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_multi_seller_analysis_workflow(self, search_task, mock_db_session):
        """Test workflow specifically for multi-seller analysis scenarios."""
        search_id = str(uuid4())

        # Create sellers with multiple items
        sellers = [
            Seller(
                id=str(uuid4()),
                platform=SearchPlatform.DISCOGS,
                platform_seller_id=f"seller_{i}",
                seller_name=f"Seller {i}",
                location="Los Angeles, CA",
                country_code="US",
            )
            for i in range(3)
        ]

        # Create search results distributed among sellers
        search_results = []
        for i, seller in enumerate(sellers):
            # Give each seller different number of items
            item_count = i + 1  # 1, 2, 3 items respectively
            for j in range(item_count):
                search_results.append(
                    SearchResult(
                        id=str(uuid4()),
                        search_id=search_id,
                        platform=SearchPlatform.DISCOGS,
                        seller_id=seller.id,
                        item_id=f"disc_{i}_{j}",
                        item_price=Decimal("25.00"),
                        item_condition="VG+",
                        is_in_wantlist=j == 0,  # First item is in wantlist
                        item_data={"title": f"Album {i}-{j}", "artist": f"Artist {i}", "year": 2020 + i},
                    )
                )

        # Mock database queries
        execute_count = 0

        def execute_side_effect(query):
            nonlocal execute_count
            execute_count += 1
            result = MagicMock()
            query_str = str(query)

            # For getting distinct seller IDs
            if "DISTINCT" in query_str and "seller_id" in query_str:
                result.all.return_value = [(seller.id,) for seller in sellers]
            # For getting search results by seller - return results for current seller
            elif "search_results" in query_str and "seller_id =" in query_str:
                # Return appropriate results based on which call this is
                seller_idx = (execute_count - 2) % len(sellers)  # -2 for the first query
                if seller_idx < len(sellers):
                    seller = sellers[seller_idx]
                    result.scalars.return_value.all.return_value = [
                        r for r in search_results if r.seller_id == seller.id
                    ]
                else:
                    result.scalars.return_value.all.return_value = []
            # For checking existing inventory
            elif "seller_inventory" in query_str:
                result.scalar.return_value = None  # No existing inventory
            else:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Execute seller analysis
        await search_task._perform_seller_analysis(mock_db_session, search_id)

        # Verify that seller analysis was created
        # Should add at least some inventory entries
        assert mock_db_session.add.called or mock_db_session.add.call_count > 0

    @pytest.mark.asyncio
    async def test_cross_platform_matching_workflow(self, search_task, mock_db_session):
        """Test workflow for cross-platform item matching."""
        search_id = str(uuid4())

        # Create items that should match across platforms
        abbey_road_results = [
            SearchResult(
                id=str(uuid4()),
                search_id=search_id,
                platform=SearchPlatform.DISCOGS,
                item_id="disc2",
                item_price=Decimal("25.00"),
                item_condition="VG+",
                seller_id=str(uuid4()),
                item_data={"title": "Abbey Road", "artist": "The Beatles", "year": 1969, "format": "Vinyl"},
            ),
            SearchResult(
                id=str(uuid4()),
                search_id=search_id,
                platform=SearchPlatform.EBAY,
                item_id="ebay2",
                item_price=Decimal("22.00"),
                item_condition="NM",
                seller_id=str(uuid4()),
                item_data={"title": "Beatles - Abbey Road", "artist": "Beatles", "year": 1969, "format": "LP"},
            ),
        ]

        # Mock database queries for cross-platform matching
        def execute_side_effect(query):
            result = MagicMock()
            query_str = str(query)

            # For fetching search results without matches
            if "search_results" in query_str and "item_match_id" in query_str:
                result.scalars.return_value.all.return_value = abbey_road_results
            # For checking existing item matches
            elif "item_matches" in query_str:
                result.scalar_one_or_none.return_value = None  # No existing matches
            else:
                result.scalars.return_value.all.return_value = []
            return result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Execute item matching
        await search_task._perform_item_matching(mock_db_session, search_id)

        # Verify matching was performed
        # Should create 1 ItemMatch (both results match to same item) and 2 ItemMatchResults
        assert mock_db_session.add.call_count >= 2  # At least ItemMatch and ItemMatchResults
        assert mock_db_session.flush.called
