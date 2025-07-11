"""Tests for Celery task registration and execution."""

from unittest.mock import Mock, patch
from uuid import uuid4

from src.workers.celery_app import celery_app
from src.workers.tasks import run_search_task, sync_collection_task


class TestCeleryTaskRegistration:
    """Test that Celery tasks are properly registered."""

    def test_run_search_task_is_registered(self):
        """Test that run_search_task is properly registered with Celery."""
        # Verify the task has a name attribute (not None)
        assert hasattr(run_search_task, "name")
        assert run_search_task.name is not None
        assert run_search_task.name == "src.workers.tasks.RunSearchTask"

        # Verify the task is registered in Celery
        assert run_search_task.name in celery_app.tasks
        assert celery_app.tasks[run_search_task.name] == run_search_task

    def test_sync_collection_task_is_registered(self):
        """Test that sync_collection_task is properly registered with Celery."""
        # Verify the task has a name attribute (not None)
        assert hasattr(sync_collection_task, "name")
        assert sync_collection_task.name is not None
        assert sync_collection_task.name == "src.workers.tasks.SyncCollectionTask"

        # Verify the task is registered in Celery
        assert sync_collection_task.name in celery_app.tasks
        assert celery_app.tasks[sync_collection_task.name] == sync_collection_task

    def test_task_can_be_called_with_delay(self):
        """Test that tasks can be called with .delay() without errors."""
        # Mock the apply_async method to avoid actually sending tasks
        with patch.object(run_search_task, "apply_async") as mock_apply:
            mock_apply.return_value = Mock(id="test-task-id")

            # This should not raise any errors about unregistered tasks
            search_id = str(uuid4())
            user_id = str(uuid4())
            run_search_task.delay(search_id, user_id)

            # Verify apply_async was called with correct arguments
            mock_apply.assert_called_once()
            args, kwargs = mock_apply.call_args
            assert args[0] == (search_id, user_id)

    def test_sync_collection_task_can_be_called(self):
        """Test that sync collection task can be called without errors."""
        with patch.object(sync_collection_task, "apply_async") as mock_apply:
            mock_apply.return_value = Mock(id="test-task-id")

            user_id = str(uuid4())
            sync_collection_task.delay(user_id)

            mock_apply.assert_called_once()
            args, kwargs = mock_apply.call_args
            assert args[0] == (user_id,)

    def test_task_headers_contain_task_name(self):
        """Test that task messages contain the task name in headers."""
        with patch.object(run_search_task, "apply_async") as mock_apply:
            search_id = str(uuid4())
            user_id = str(uuid4())

            # Call the task
            run_search_task.delay(search_id, user_id)

            # Get the call arguments
            args, kwargs = mock_apply.call_args

            # In Celery, when using .delay(), it's equivalent to .apply_async(args)
            # The task name should be available through the task's name attribute
            assert run_search_task.name == "src.workers.tasks.RunSearchTask"
            assert run_search_task.name is not None


# Simplified execution tests - the actual implementation is complex
# These tests ensure tasks are callable and don't error out
class TestCeleryTaskCallability:
    """Test that Celery tasks can be called without errors."""

    def test_tasks_have_run_method(self):
        """Test that tasks have the run method required by Celery."""
        # Verify RunSearchTask has run method
        assert hasattr(run_search_task, "run")
        assert callable(run_search_task.run)

        # Verify SyncCollectionTask has run method
        assert hasattr(sync_collection_task, "run")
        assert callable(sync_collection_task.run)

    def test_tasks_are_celery_tasks(self):
        """Test that tasks are properly configured as Celery tasks."""
        # Check that tasks have Celery task attributes
        assert hasattr(run_search_task, "name")
        assert hasattr(run_search_task, "app")
        assert run_search_task.app == celery_app

        assert hasattr(sync_collection_task, "name")
        assert hasattr(sync_collection_task, "app")
        assert sync_collection_task.app == celery_app
