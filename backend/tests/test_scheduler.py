"""Tests for scheduler module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch
from src.workers.scheduler import async_main, check_scheduled_searches, main


class TestScheduler:
    """Test suite for scheduler functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_search(self):
        """Create a sample saved search."""
        return SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="test query",
            is_active=True,
            check_interval_hours=24,
            last_run_at=None,
        )

    @pytest.fixture
    def old_search(self):
        """Create a search that was last run 25 hours ago."""
        return SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="old query",
            is_active=True,
            check_interval_hours=24,
            last_run_at=datetime.now(UTC) - timedelta(hours=25),
        )

    @pytest.fixture
    def recent_search(self):
        """Create a search that was last run 1 hour ago."""
        return SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="recent query",
            is_active=True,
            check_interval_hours=24,
            last_run_at=datetime.now(UTC) - timedelta(hours=1),
        )

    @pytest.fixture
    def inactive_search(self):
        """Create an inactive search."""
        return SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="inactive query",
            is_active=False,
            check_interval_hours=24,
            last_run_at=None,
        )

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_first_run(self, sample_search):
        """Test scheduling a search that has never been run."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            # Mock database session and result
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [sample_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify database query was made
            mock_db.execute.assert_called_once()

            # Verify task was queued
            mock_task.delay.assert_called_once_with(str(sample_search.id), str(sample_search.user_id))

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_old_search(self, old_search):
        """Test scheduling a search that was last run long ago."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [old_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify task was queued for old search
            mock_task.delay.assert_called_once_with(str(old_search.id), str(old_search.user_id))

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_recent_search(self, recent_search):
        """Test that recent searches are not scheduled."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [recent_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify task was not queued for recent search
            mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_multiple_searches(self, sample_search, old_search, recent_search):
        """Test scheduling multiple searches with different timing."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [sample_search, old_search, recent_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify tasks were queued for first-run and old searches only
            assert mock_task.delay.call_count == 2
            expected_calls = [
                (str(sample_search.id), str(sample_search.user_id)),
                (str(old_search.id), str(old_search.user_id)),
            ]
            actual_calls = [call.args for call in mock_task.delay.call_args_list]
            assert actual_calls == expected_calls

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_custom_interval(self):
        """Test search with custom check interval."""
        # Create search with 6-hour interval that was last run 7 hours ago
        custom_search = SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="custom interval query",
            is_active=True,
            check_interval_hours=6,
            last_run_at=datetime.now(UTC) - timedelta(hours=7),
        )

        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [custom_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Should be scheduled because 7 hours > 6 hour interval
            mock_task.delay.assert_called_once_with(str(custom_search.id), str(custom_search.user_id))

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_custom_interval_too_recent(self):
        """Test search with custom interval that was run too recently."""
        # Create search with 6-hour interval that was last run 3 hours ago
        custom_search = SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="custom interval query",
            is_active=True,
            check_interval_hours=6,
            last_run_at=datetime.now(UTC) - timedelta(hours=3),
        )

        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [custom_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Should not be scheduled because 3 hours < 6 hour interval
            mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_empty_result(self):
        """Test when no searches need to be scheduled."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify no tasks were queued
            mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_database_error(self):
        """Test error handling when database query fails."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
            patch("src.workers.scheduler.logger") as mock_logger,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            # Simulate database error
            mock_db.execute.side_effect = Exception("Database connection failed")

            await check_scheduled_searches()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Error checking scheduled searches" in error_message
            assert "Database connection failed" in error_message

            # Verify no tasks were queued
            mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_query_structure(self):
        """Test that the database query has correct structure."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task"),
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify database query was called
            mock_db.execute.assert_called_once()
            # Query should be for active searches that haven't run recently

    @pytest.mark.asyncio
    async def test_async_main_scheduler_setup(self):
        """Test that async_main sets up the scheduler correctly."""
        with (
            patch("src.workers.scheduler.AsyncIOScheduler") as mock_scheduler_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            # Make sleep raise exception to exit the loop
            mock_sleep.side_effect = KeyboardInterrupt()

            try:
                await async_main()
            except KeyboardInterrupt:
                pass

            # Verify scheduler was configured correctly
            mock_scheduler.add_job.assert_called_once()
            call_args = mock_scheduler.add_job.call_args

            # Check job function
            assert call_args[0][0] == check_scheduled_searches

            # Check job configuration
            kwargs = call_args[1]
            assert kwargs["hours"] == 1
            assert kwargs["id"] == "check_searches"
            assert kwargs["replace_existing"] is True

            # Verify scheduler was started
            mock_scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_main_keyboard_interrupt(self):
        """Test that async_main handles KeyboardInterrupt correctly."""
        with (
            patch("src.workers.scheduler.AsyncIOScheduler") as mock_scheduler_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            # Simulate KeyboardInterrupt during the sleep loop
            mock_sleep.side_effect = KeyboardInterrupt()

            await async_main()

            # Verify scheduler was shut down
            mock_scheduler.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_main_system_exit(self):
        """Test that async_main handles SystemExit correctly."""
        with (
            patch("src.workers.scheduler.AsyncIOScheduler") as mock_scheduler_class,
            patch("asyncio.sleep") as mock_sleep,
        ):
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            # Simulate SystemExit during the sleep loop
            mock_sleep.side_effect = SystemExit()

            await async_main()

            # Verify scheduler was shut down
            mock_scheduler.shutdown.assert_called_once()

    def test_main_function(self):
        """Test that main function calls asyncio.run with async_main."""
        with patch("asyncio.run") as mock_run:
            main()

            # Verify asyncio.run was called once
            mock_run.assert_called_once()

            # Verify the argument was a coroutine from async_main function
            call_args = mock_run.call_args[0][0]
            assert hasattr(call_args, "__name__")
            assert call_args.__name__ == "async_main"

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_logging(self, sample_search):
        """Test that appropriate log messages are generated."""
        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task"),
            patch("src.workers.scheduler.logger") as mock_logger,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [sample_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Verify logging calls
            mock_logger.info.assert_any_call("Checking for scheduled searches")
            mock_logger.info.assert_any_call(f"Queueing search {sample_search.id}")

    @pytest.mark.asyncio
    async def test_check_scheduled_searches_timezone_handling(self):
        """Test that datetime comparisons handle UTC correctly."""
        # Create search with UTC timezone aware datetime
        utc_search = SavedSearch(
            id=uuid4(),
            user_id=uuid4(),
            query="utc query",
            is_active=True,
            check_interval_hours=24,
            last_run_at=datetime.now(UTC) - timedelta(hours=25),
        )

        with (
            patch("src.workers.scheduler.AsyncSessionLocal") as mock_session_local,
            patch("src.workers.scheduler.run_search_task") as mock_task,
        ):
            mock_db = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [utc_search]
            mock_db.execute.return_value = mock_result

            await check_scheduled_searches()

            # Should be scheduled because time difference calculation should work correctly
            mock_task.delay.assert_called_once_with(str(utc_search.id), str(utc_search.user_id))
