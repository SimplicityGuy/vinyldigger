from uuid import UUID

from src.workers.tasks import run_search_task


class SearchService:
    async def queue_search(self, search_id: UUID, user_id: UUID) -> None:
        # Queue the search task for background processing
        run_search_task.delay(str(search_id), str(user_id))