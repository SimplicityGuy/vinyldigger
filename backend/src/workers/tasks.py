import asyncio
from datetime import datetime
from uuid import UUID

from celery import Task

from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.models.search import SavedSearch
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


class AsyncTask(Task):
    def run(self, *args, **kwargs):
        return asyncio.run(self.async_run(*args, **kwargs))

    async def async_run(self, *args, **kwargs):
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncTask)
class RunSearchTask(AsyncTask):
    async def async_run(self, search_id: str, user_id: str):
        logger.info(f"Running search {search_id} for user {user_id}")
        async with AsyncSessionLocal() as db:
            try:
                # Get search details
                search = await db.get(SavedSearch, UUID(search_id))
                if not search:
                    logger.error(f"Search {search_id} not found")
                    return

                # TODO: Implement actual search logic with eBay/Discogs APIs
                # For now, just update last_checked_at
                search.last_checked_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Search {search_id} completed successfully")
            except Exception as e:
                logger.error(f"Error running search {search_id}: {str(e)}")
                raise


@celery_app.task(bind=True, base=AsyncTask)
class SyncCollectionTask(AsyncTask):
    async def async_run(self, user_id: str):
        logger.info(f"Syncing collection for user {user_id}")
        async with AsyncSessionLocal() as db:
            try:
                # TODO: Implement actual Discogs sync logic
                logger.info(f"Collection sync for user {user_id} completed")
            except Exception as e:
                logger.error(f"Error syncing collection for user {user_id}: {str(e)}")
                raise


run_search_task = RunSearchTask()
sync_collection_task = SyncCollectionTask()