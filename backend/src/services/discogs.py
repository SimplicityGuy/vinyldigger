from uuid import UUID

from src.workers.tasks import sync_collection_task


class DiscogsService:
    async def queue_sync(self, user_id: UUID) -> None:
        # Queue the sync task for background processing
        sync_collection_task.delay(str(user_id))
