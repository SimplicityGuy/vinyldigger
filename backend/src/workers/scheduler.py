import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.models.search import SavedSearch
from src.models.search_chain import SearchChain
from src.services.search_orchestrator import SearchOrchestrator
from src.workers.tasks import run_search_task

logger = get_logger(__name__)


async def check_scheduled_searches() -> None:
    logger.info("Checking for scheduled searches and orchestration")
    orchestrator = SearchOrchestrator()

    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(UTC)

            # 1. Check individual searches (existing logic with orchestration enhancements)
            await _check_individual_searches(db, orchestrator, now)

            # 2. Check search chains for trigger conditions
            await _check_search_chains(db, orchestrator)

            # 3. Check dependent searches
            await _check_dependent_searches(db, orchestrator)

        except Exception as e:
            logger.error(f"Error checking scheduled searches: {str(e)}")


async def _check_individual_searches(db, orchestrator: SearchOrchestrator, now: datetime) -> None:
    """Check individual searches for scheduling."""
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
            # Check budget constraints before running
            estimated_cost = search.estimated_cost_per_result * Decimal("10")  # Estimate 10 results

            if await orchestrator.check_budget_constraints(db, search.user_id, estimated_cost):
                # Check optimal timing
                optimal_time = await orchestrator.get_optimal_schedule_time(search)

                if optimal_time <= now + timedelta(minutes=30):  # Allow 30min window
                    logger.info(f"Queueing search {search.id} ({search.name})")
                    run_search_task.delay(str(search.id), str(search.user_id))
                else:
                    logger.info(f"Search {search.id} scheduled for optimal time: {optimal_time}")
            else:
                logger.info(f"Search {search.id} skipped due to budget constraints")


async def _check_search_chains(db, orchestrator: SearchOrchestrator) -> None:
    """Check search chains for trigger conditions."""
    chains_result = await db.execute(select(SearchChain).where(SearchChain.is_active.is_(True)))
    chains = chains_result.scalars().all()

    for chain in chains:
        try:
            searches_to_trigger = await orchestrator.evaluate_chain_triggers(db, chain.id)

            for search_id in searches_to_trigger:
                search_result = await db.execute(select(SavedSearch).where(SavedSearch.id == search_id))
                search = search_result.scalar_one_or_none()

                if search:
                    # Check budget before triggering
                    estimated_cost = search.estimated_cost_per_result * Decimal("10")

                    if await orchestrator.check_budget_constraints(db, search.user_id, estimated_cost):
                        logger.info(f"Triggering chained search {search.id} from chain {chain.name}")
                        run_search_task.delay(str(search.id), str(search.user_id))
                    else:
                        logger.info(f"Chained search {search.id} blocked by budget constraints")

        except Exception as e:
            logger.error(f"Error processing chain {chain.id}: {str(e)}")


async def _check_dependent_searches(db, orchestrator: SearchOrchestrator) -> None:
    """Check for searches that depend on recently completed searches."""
    # Find searches that have run in the last hour
    now = datetime.now(UTC)
    recent_searches_result = await db.execute(
        select(SavedSearch).where(SavedSearch.last_run_at >= now - timedelta(hours=1), SavedSearch.is_active.is_(True))
    )
    recent_searches = recent_searches_result.scalars().all()

    for parent_search in recent_searches:
        dependent_searches = await orchestrator.get_dependent_searches(db, parent_search.id)

        for dependent_search in dependent_searches:
            should_trigger = await orchestrator.should_trigger_dependent_search(db, dependent_search, parent_search.id)

            if should_trigger:
                # Check budget
                estimated_cost = dependent_search.estimated_cost_per_result * Decimal("10")

                if await orchestrator.check_budget_constraints(db, dependent_search.user_id, estimated_cost):
                    logger.info(f"Triggering dependent search {dependent_search.id} based on parent {parent_search.id}")
                    run_search_task.delay(str(dependent_search.id), str(dependent_search.user_id))
                else:
                    logger.info(f"Dependent search {dependent_search.id} blocked by budget constraints")


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
