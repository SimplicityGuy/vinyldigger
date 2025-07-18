"""Integration tests for search orchestration features."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform
from src.models.search_budget import SearchBudget
from src.models.search_chain import SearchChain, SearchChainLink
from src.models.search_template import SearchTemplate
from src.models.user import User
from src.services.search_orchestrator import SearchOrchestrator
from src.workers.tasks import RunSearchTask


@pytest.fixture
async def orchestrator():
    """Create orchestrator instance."""
    return SearchOrchestrator()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="orchestration_test@example.com",
        username="orchestration_test",
        hashed_password="test_hash",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_budget(db_session: AsyncSession, test_user: User) -> SearchBudget:
    """Create a test budget."""
    budget = SearchBudget(
        id=uuid4(),
        user_id=test_user.id,
        monthly_limit=Decimal("50.00"),
        current_spent=Decimal("20.00"),
        period_start=datetime.now(UTC) - timedelta(days=5),
        period_end=datetime.now(UTC) + timedelta(days=25),
        is_active=True,
    )
    db_session.add(budget)
    await db_session.commit()
    return budget


@pytest.fixture
async def test_template(db_session: AsyncSession, test_user: User) -> SearchTemplate:
    """Create a test template."""
    template = SearchTemplate(
        id=uuid4(),
        name="Jazz Records Template",
        description="Search for jazz vinyl records",
        category="Jazz",
        is_public=True,
        created_by=test_user.id,
        template_data={
            "query": "{artist} {album} jazz vinyl",
            "platform": "both",
            "min_price": 10,
            "max_price": 100,
            "check_interval_hours": 24,
            "filters": {"genre": "jazz", "format": "LP"},
        },
        parameters={
            "artist": {"type": "string", "required": True, "description": "Artist name"},
            "album": {"type": "string", "required": False, "default": "", "description": "Album name"},
        },
    )
    db_session.add(template)
    await db_session.commit()
    return template


@pytest.fixture
async def test_search(db_session: AsyncSession, test_user: User, test_budget: SearchBudget) -> SavedSearch:
    """Create a test search."""
    search = SavedSearch(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Jazz Search",
        query="Miles Davis Kind of Blue",
        platform=SearchPlatform.BOTH,
        filters={"genre": "jazz"},
        min_price=Decimal("10.00"),
        max_price=Decimal("100.00"),
        check_interval_hours=24,
        is_active=True,
        budget_id=test_budget.id,
        estimated_cost_per_result=Decimal("0.10"),
        priority_level=7,
    )
    db_session.add(search)
    await db_session.commit()
    return search


class TestBudgetConstraints:
    """Test budget constraint checking."""

    async def test_check_budget_constraints_within_limit(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_budget: SearchBudget
    ):
        """Test budget check when within limits."""
        # Budget has $30 remaining (50 - 20)
        result = await orchestrator.check_budget_constraints(db_session, test_user.id, Decimal("25.00"))
        assert result is True

    async def test_check_budget_constraints_exceeds_limit(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_budget: SearchBudget
    ):
        """Test budget check when exceeding limits."""
        # Budget has $30 remaining (50 - 20)
        result = await orchestrator.check_budget_constraints(db_session, test_user.id, Decimal("35.00"))
        assert result is False

    async def test_check_budget_constraints_no_budget(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User
    ):
        """Test budget check when no budget is set."""
        # User has no budget, should allow unlimited
        result = await orchestrator.check_budget_constraints(db_session, test_user.id, Decimal("1000.00"))
        assert result is True

    async def test_update_budget_spending(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_budget: SearchBudget
    ):
        """Test updating budget spending."""
        initial_spent = test_budget.current_spent

        await orchestrator.update_budget_spending(db_session, test_user.id, Decimal("5.50"))
        await db_session.commit()

        # Refresh budget
        await db_session.refresh(test_budget)
        assert test_budget.current_spent == initial_spent + Decimal("5.50")


class TestTemplateUsage:
    """Test template creation and usage."""

    async def test_create_search_from_template(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_template: SearchTemplate
    ):
        """Test creating a search from a template."""
        params = {"artist": "John Coltrane", "album": "A Love Supreme"}

        search = await orchestrator.create_search_from_template(db_session, test_template.id, test_user.id, params)

        assert search.user_id == test_user.id
        assert search.query == "John Coltrane A Love Supreme jazz vinyl"
        assert search.platform == SearchPlatform.BOTH
        assert search.min_price == Decimal("10")
        assert search.max_price == Decimal("100")
        assert search.template_id == test_template.id
        assert search.filters == {"genre": "jazz", "format": "LP"}

    async def test_create_search_from_template_with_defaults(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_template: SearchTemplate
    ):
        """Test creating a search from template using default values."""
        params = {
            "artist": "Bill Evans"  # Only required parameter
        }

        search = await orchestrator.create_search_from_template(db_session, test_template.id, test_user.id, params)

        assert search.query == "Bill Evans  jazz vinyl"  # album default is empty string

    async def test_create_search_from_template_missing_required(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_template: SearchTemplate
    ):
        """Test creating a search from template with missing required parameter."""
        params = {
            "album": "Blue Train"  # Missing required 'artist'
        }

        with pytest.raises(ValueError, match="Required parameter 'artist' not provided"):
            await orchestrator.create_search_from_template(db_session, test_template.id, test_user.id, params)


class TestSearchChains:
    """Test search chain evaluation."""

    async def test_evaluate_chain_triggers_simple(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User
    ):
        """Test evaluating simple chain triggers."""
        # Create chain
        chain = SearchChain(
            id=uuid4(),
            user_id=test_user.id,
            name="Test Chain",
            description="Test chain description",
            is_active=True,
        )
        db_session.add(chain)

        # Create searches
        search1 = SavedSearch(
            id=uuid4(),
            user_id=test_user.id,
            name="Search 1",
            query="test query 1",
            platform=SearchPlatform.BOTH,
            is_active=True,
        )
        search2 = SavedSearch(
            id=uuid4(),
            user_id=test_user.id,
            name="Search 2",
            query="test query 2",
            platform=SearchPlatform.BOTH,
            is_active=True,
        )
        db_session.add_all([search1, search2])

        # Create chain links
        link1 = SearchChainLink(
            id=uuid4(),
            chain_id=chain.id,
            search_id=search1.id,
            order_index=1,
            trigger_condition={},  # No conditions, always trigger
        )
        link2 = SearchChainLink(
            id=uuid4(),
            chain_id=chain.id,
            search_id=search2.id,
            order_index=2,
            trigger_condition={},  # No conditions, always trigger
        )
        db_session.add_all([link1, link2])
        await db_session.commit()

        # Evaluate triggers
        triggered = await orchestrator.evaluate_chain_triggers(db_session, chain.id)

        assert len(triggered) == 2
        assert search1.id in triggered
        assert search2.id in triggered

    async def test_evaluate_chain_triggers_with_conditions(
        self, db_session: AsyncSession, orchestrator: SearchOrchestrator, test_user: User, test_search: SavedSearch
    ):
        """Test evaluating chain triggers with conditions."""
        # Create parent search with results
        from src.models.search import SearchResult

        for i in range(10):
            result = SearchResult(
                id=uuid4(),
                search_id=test_search.id,
                platform=SearchPlatform.DISCOGS,
                item_id=f"item_{i}",
                item_data={"title": f"Test Item {i}"},
                item_price=Decimal(str(20 + i * 5)),
                is_in_wantlist=(i % 2 == 0),  # Even items in wantlist
            )
            db_session.add(result)

        # Create dependent search
        dependent_search = SavedSearch(
            id=uuid4(),
            user_id=test_user.id,
            name="Dependent Search",
            query="dependent query",
            platform=SearchPlatform.BOTH,
            depends_on_search=test_search.id,
            trigger_conditions={"min_results": 5, "max_price": 50, "found_in_wantlist": True},
            is_active=True,
        )
        db_session.add(dependent_search)
        await db_session.commit()

        # Test trigger evaluation
        should_trigger = await orchestrator.should_trigger_dependent_search(
            db_session, dependent_search, test_search.id
        )

        assert should_trigger is True  # Has 10 results, some under $50, some in wantlist


class TestOptimalScheduling:
    """Test optimal schedule time calculation."""

    async def test_get_optimal_schedule_time_with_preferences(
        self, orchestrator: SearchOrchestrator, test_search: SavedSearch
    ):
        """Test calculating optimal schedule time with preferences."""
        # Set optimal run times
        test_search.optimal_run_times = [9, 14, 20]  # 9am, 2pm, 8pm
        test_search.check_interval_hours = 24

        # Test at 10am - should schedule for 2pm today
        now = datetime.now(UTC).replace(hour=10, minute=0, second=0, microsecond=0)
        optimal_time = await orchestrator.get_optimal_schedule_time(test_search)

        assert optimal_time.hour == 14
        assert optimal_time.date() == now.date()

    async def test_get_optimal_schedule_time_avoid_times(
        self, orchestrator: SearchOrchestrator, test_search: SavedSearch
    ):
        """Test calculating schedule time while avoiding certain hours."""
        # Set avoid times
        test_search.avoid_run_times = [0, 1, 2, 3, 4, 5]  # Avoid midnight to 5am
        test_search.check_interval_hours = 4

        # If base calculation would be 2am, should shift to 6am

        optimal_time = await orchestrator.get_optimal_schedule_time(test_search)

        assert optimal_time.hour not in test_search.avoid_run_times


class TestSearchExecution:
    """Test search execution with orchestration."""

    @pytest.mark.asyncio
    async def test_search_execution_with_budget_constraint(
        self, db_session: AsyncSession, test_user: User, test_search: SavedSearch, test_budget: SearchBudget
    ):
        """Test search execution respects budget constraints."""
        # Set budget to be almost exhausted
        test_budget.current_spent = Decimal("49.00")  # Only $1 remaining
        test_search.estimated_cost_per_result = Decimal("0.10")
        await db_session.commit()

        # Create task instance
        task = RunSearchTask()

        # Mock the search services to avoid external API calls
        async def mock_search(*args, **kwargs):
            return []  # Return empty results

        # Use patch to mock search methods
        with patch.object(task, "_search_discogs", mock_search), patch.object(task, "_search_ebay", mock_search):
            # Execute search
            await task.async_run(str(test_search.id), str(test_user.id))

            # Refresh search to check status
            await db_session.refresh(test_search)

            # Should be marked as budget_exceeded
            assert test_search.status == "budget_exceeded"
            assert test_search.last_run_at is not None

    @pytest.mark.asyncio
    async def test_search_execution_updates_budget(
        self, db_session: AsyncSession, test_user: User, test_search: SavedSearch, test_budget: SearchBudget
    ):
        """Test search execution updates budget spending."""
        initial_spent = test_budget.current_spent

        # Create task instance
        task = RunSearchTask()

        # Mock the search services to return some results
        async def mock_search_discogs(*args, **kwargs):
            return [
                {"id": "123", "title": "Test Item 1", "price": 25.00},
                {"id": "456", "title": "Test Item 2", "price": 30.00},
            ]

        async def mock_search_ebay(*args, **kwargs):
            return []

        # Use patch to mock search methods
        with (
            patch.object(task, "_search_discogs", mock_search_discogs),
            patch.object(task, "_search_ebay", mock_search_ebay),
        ):
            # Execute search
            await task.async_run(str(test_search.id), str(test_user.id))

            # Refresh budget to check spending
            await db_session.refresh(test_budget)

            # Should have added cost for 2 results
            expected_cost = test_search.estimated_cost_per_result * 2
            assert test_budget.current_spent == initial_spent + expected_cost
