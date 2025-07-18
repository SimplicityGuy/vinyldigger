import asyncio
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.models.search import SavedSearch
from src.workers.tasks import run_search_task

logger = get_logger(__name__)


async def check_scheduled_searches() -> None:
    logger.info("Checking for scheduled searches")
    async with AsyncSessionLocal() as db:
        try:
            # Find searches that need to be run
            now = datetime.now(UTC)
            result = await db.execute(
                select(SavedSearch).where(
                    SavedSearch.is_active,
                    (SavedSearch.last_run_at.is_(None)) | (SavedSearch.last_run_at < now - timedelta(hours=1)),
                )
            )
            searches = result.scalars().all()

            for search in searches:
                if search.last_run_at is None:
                    # First run
                    should_run = True
                else:
                    # Check if enough time has passed
                    time_since_last = now - search.last_run_at
                    should_run = time_since_last >= timedelta(hours=search.check_interval_hours)

                if should_run:
                    logger.info(f"Queueing search {search.id}")
                    run_search_task.delay(str(search.id), str(search.user_id))

        except Exception as e:
            logger.error(f"Error checking scheduled searches: {str(e)}")


async def async_main() -> None:
    scheduler = AsyncIOScheduler()

    # Run every hour
    scheduler.add_job(
        check_scheduled_searches,
        "interval",
        hours=1,
        id="check_searches",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")

    try:
        # Keep the event loop running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
