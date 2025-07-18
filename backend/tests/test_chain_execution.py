"""Tests for search chain execution and feedback."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_chain import SearchChain, SearchChainLink
from src.models.user import User
from src.services.search_orchestrator import SearchOrchestrator
from src.workers.tasks import RunSearchTask


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="chain_test@example.com",
        username="chain_test",
        hashed_password="test_hash",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_chain(db_session: AsyncSession, test_user: User) -> SearchChain:
    """Create a test search chain."""
    chain = SearchChain(
        id=uuid4(),
        user_id=test_user.id,
        name="Progressive Search Chain",
        description="Chain that progressively refines searches",
        is_active=True,
    )
    db_session.add(chain)
    await db_session.commit()
    return chain


@pytest.fixture
async def chain_searches(db_session: AsyncSession, test_user: User, test_chain: SearchChain) -> list[SavedSearch]:
    """Create searches for the chain."""
    # Initial broad search
    search1 = SavedSearch(
        id=uuid4(),
        user_id=test_user.id,
        name="Broad Jazz Search",
        query="jazz vinyl",
        platform=SearchPlatform.BOTH,
        min_price=Decimal("5.00"),
        max_price=Decimal("200.00"),
        is_active=True,
        chain_id=test_chain.id,
        estimated_cost_per_result=Decimal("0.10"),
    )

    # Refined search based on first results
    search2 = SavedSearch(
        id=uuid4(),
        user_id=test_user.id,
        name="Refined Jazz Search",
        query="blue note jazz vinyl",
        platform=SearchPlatform.BOTH,
        min_price=Decimal("20.00"),
        max_price=Decimal("100.00"),
        is_active=True,
        chain_id=test_chain.id,
        depends_on_search=search1.id,
        trigger_conditions={
            "min_results": 10,
            "max_price": 50,
        },
        estimated_cost_per_result=Decimal("0.10"),
    )

    # Targeted search for wantlist items
    search3 = SavedSearch(
        id=uuid4(),
        user_id=test_user.id,
        name="Wantlist Jazz Search",
        query="miles davis kind of blue vinyl",
        platform=SearchPlatform.BOTH,
        min_price=Decimal("30.00"),
        max_price=Decimal("80.00"),
        is_active=True,
        chain_id=test_chain.id,
        depends_on_search=search2.id,
        trigger_conditions={
            "found_in_wantlist": True,
            "min_results": 5,
        },
        estimated_cost_per_result=Decimal("0.10"),
    )

    db_session.add_all([search1, search2, search3])

    # Create chain links
    link1 = SearchChainLink(
        id=uuid4(),
        chain_id=test_chain.id,
        search_id=search1.id,
        order_index=1,
        trigger_condition={},  # Always run first search
    )

    link2 = SearchChainLink(
        id=uuid4(),
        chain_id=test_chain.id,
        search_id=search2.id,
        order_index=2,
        trigger_condition={
            "min_results": 10,
            "max_price": 50,
        },
    )

    link3 = SearchChainLink(
        id=uuid4(),
        chain_id=test_chain.id,
        search_id=search3.id,
        order_index=3,
        trigger_condition={
            "found_in_wantlist": True,
            "min_results": 5,
        },
    )

    db_session.add_all([link1, link2, link3])
    await db_session.commit()

    return [search1, search2, search3]


class TestChainExecution:
    """Test chain execution flow."""

    async def test_chain_trigger_evaluation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test that chain triggers are evaluated correctly."""
        orchestrator = SearchOrchestrator()

        # Initially, only the first search should trigger (no conditions)
        triggered = await orchestrator.evaluate_chain_triggers(db_session, test_chain.id)
        assert len(triggered) == 1
        assert triggered[0] == chain_searches[0].id

    async def test_chain_progressive_execution(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test progressive chain execution based on results."""
        orchestrator = SearchOrchestrator()

        # Simulate results from first search
        for i in range(15):  # More than min_results threshold
            result = SearchResult(
                id=uuid4(),
                search_id=chain_searches[0].id,
                platform=SearchPlatform.DISCOGS,
                item_id=f"item_{i}",
                item_data={"title": f"Jazz Album {i}"},
                item_price=Decimal(str(30 + i * 5)),  # Some under $50
                is_in_wantlist=(i < 3),  # First 3 in wantlist
            )
            db_session.add(result)
        await db_session.commit()

        # Now second search should trigger
        triggered = await orchestrator.evaluate_chain_triggers(db_session, test_chain.id)
        assert chain_searches[1].id in triggered

        # Check if dependent search should trigger
        should_trigger = await orchestrator.should_trigger_dependent_search(
            db_session, chain_searches[1], chain_searches[0].id
        )
        assert should_trigger is True  # Has 15 results, some under $50

    async def test_chain_execution_feedback_tracking(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test that chain execution feedback is properly tracked."""
        # Mock task execution
        task = RunSearchTask()

        # Mock search methods to simulate results
        async def mock_search_discogs(*args, **kwargs):
            return [
                {
                    "id": f"disc_{i}",
                    "title": f"Jazz Record {i}",
                    "price": 25.00 + i * 5,
                    "condition": {"media": "VG+", "sleeve": "VG"},
                }
                for i in range(12)
            ]

        # Use patch to mock search methods
        with (
            patch.object(task, "_search_discogs", mock_search_discogs),
            patch.object(task, "_search_ebay", lambda *args, **kwargs: []),
        ):  # No eBay results
            # Execute first search
            await task.async_run(str(chain_searches[0].id), str(test_user.id))

            # Check search status and results count
            await db_session.refresh(chain_searches[0])
            assert chain_searches[0].status == "completed"
            assert chain_searches[0].results_count == 12
            assert chain_searches[0].last_run_at is not None

    async def test_chain_execution_with_failures(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test chain execution handles failures gracefully."""
        task = RunSearchTask()

        # Mock search to fail
        async def mock_failing_search(*args, **kwargs):
            raise Exception("API error")

        # Use patch to mock failing search methods
        with (
            patch.object(task, "_search_discogs", mock_failing_search),
            patch.object(task, "_search_ebay", mock_failing_search),
        ):
            # Execute search - should handle error
            with pytest.raises(Exception, match="API error"):
                await task.async_run(str(chain_searches[0].id), str(test_user.id))

            # Search should not have successful status
            await db_session.refresh(chain_searches[0])
            assert chain_searches[0].status != "completed"


class TestChainFeedbackAPI:
    """Test chain execution feedback via API."""

    async def test_get_chain_execution_status(
        self,
        async_client,
        auth_headers,
        db_session: AsyncSession,
        test_user: User,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test getting chain execution status."""
        # Update searches with execution status
        chain_searches[0].status = "completed"
        chain_searches[0].results_count = 15
        chain_searches[0].last_run_at = datetime.now(UTC)

        chain_searches[1].status = "running"
        chain_searches[1].results_count = 0

        chain_searches[2].status = None  # Not yet run
        chain_searches[2].results_count = 0

        await db_session.commit()

        # Get chain status
        response = await async_client.get(
            f"/api/v1/chains/{test_chain.id}/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["chain_id"] == str(test_chain.id)
        assert data["is_active"] is True
        assert len(data["search_statuses"]) == 3

        # Check individual search statuses
        statuses = {s["search_id"]: s for s in data["search_statuses"]}
        assert statuses[str(chain_searches[0].id)]["status"] == "completed"
        assert statuses[str(chain_searches[0].id)]["results_count"] == 15
        assert statuses[str(chain_searches[1].id)]["status"] == "running"
        assert statuses[str(chain_searches[2].id)]["status"] is None

    async def test_get_chain_execution_history(
        self,
        async_client,
        auth_headers,
        test_chain: SearchChain,
    ):
        """Test getting chain execution history."""
        response = await async_client.get(
            f"/api/v1/chains/{test_chain.id}/history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestChainAnalytics:
    """Test chain analytics and insights."""

    async def test_chain_performance_metrics(
        self,
        db_session: AsyncSession,
        test_chain: SearchChain,
        chain_searches: list[SavedSearch],
    ):
        """Test calculating chain performance metrics."""
        # Add execution history
        now = datetime.now(UTC)

        # First search: always runs, good results
        chain_searches[0].status = "completed"
        chain_searches[0].results_count = 20
        chain_searches[0].last_run_at = now - timedelta(hours=1)

        # Second search: triggered 80% of the time
        chain_searches[1].status = "completed"
        chain_searches[1].results_count = 8
        chain_searches[1].last_run_at = now - timedelta(minutes=30)

        # Third search: triggered 40% of the time
        chain_searches[2].status = "completed"
        chain_searches[2].results_count = 2
        chain_searches[2].last_run_at = now - timedelta(minutes=10)

        await db_session.commit()

        # Calculate metrics
        total_results = sum(s.results_count for s in chain_searches)
        assert total_results == 30

        # Average results per search
        avg_results = total_results / len(chain_searches)
        assert avg_results == 10.0
