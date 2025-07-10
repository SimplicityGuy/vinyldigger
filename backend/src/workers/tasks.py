import asyncio
import threading
from datetime import datetime
from typing import Any
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger
from src.models.collection import Collection, WantList
from src.models.price_history import PriceHistory
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.services.discogs import DiscogsService
from src.services.ebay import EbayService
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


class AsyncTask(Task):  # type: ignore[misc]
    def run(self, *args: Any, **kwargs: Any) -> Any:
        return asyncio.run(self.async_run(*args, **kwargs))

    async def async_run(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class RunSearchTask(AsyncTask):
    async def async_run(self, search_id: str, user_id: str) -> None:
        logger.info(f"Running search {search_id} for user {user_id}")
        async with AsyncSessionLocal() as db:
            try:
                # Get search details
                search = await db.get(SavedSearch, UUID(search_id))
                if not search:
                    logger.error(f"Search {search_id} not found")
                    return

                # Check user's collection and want list for matching
                collection_items = await db.execute(select(Collection).where(Collection.user_id == UUID(user_id)))
                collection_releases = {
                    item.discogs_data.get("release_id") or item.discogs_data.get("id")
                    for item in collection_items.scalars()
                    if item.discogs_data
                }

                wantlist_items = await db.execute(select(WantList).where(WantList.user_id == UUID(user_id)))
                wantlist_releases = {
                    item.discogs_data.get("release_id") or item.discogs_data.get("id")
                    for item in wantlist_items.scalars()
                    if item.discogs_data
                }

                results_added = 0

                # Run searches based on platform
                if search.platform in [SearchPlatform.DISCOGS, SearchPlatform.BOTH]:
                    results_added += await self._search_discogs(
                        db, search, user_id, collection_releases, wantlist_releases
                    )

                if search.platform in [SearchPlatform.EBAY, SearchPlatform.BOTH]:
                    results_added += await self._search_ebay(
                        db, search, user_id, collection_releases, wantlist_releases
                    )

                # Update last_checked_at
                search.last_checked_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Search {search_id} completed successfully. Added {results_added} new results.")
            except Exception as e:
                logger.error(f"Error running search {search_id}: {str(e)}")
                await db.rollback()
                raise

    async def _search_discogs(
        self,
        db: AsyncSession,
        search: SavedSearch,
        user_id: str,
        collection_releases: set[Any],
        wantlist_releases: set[Any],
    ) -> int:
        results_added = 0

        try:
            async with DiscogsService() as service:
                credentials = await service.get_api_credentials(db, UUID(user_id))
                if not credentials:
                    logger.warning(f"No Discogs credentials for user {user_id}")
                    return 0

                items = await service.search(search.query, search.filters, credentials)

                for item in items:
                    # Check if we already have this result
                    existing = await db.execute(
                        select(SearchResult).where(
                            SearchResult.search_id == search.id,
                            SearchResult.item_id == str(item["id"]),
                            SearchResult.platform == SearchPlatform.DISCOGS,
                        )
                    )
                    if existing.scalar():
                        continue

                    # Create search result
                    result = SearchResult(
                        search_id=search.id,
                        platform=SearchPlatform.DISCOGS,
                        item_id=str(item["id"]),
                        item_data=item,
                        is_in_collection=item.get("id") in collection_releases,
                        is_in_wantlist=item.get("id") in wantlist_releases,
                    )
                    db.add(result)
                    results_added += 1

        except Exception as e:
            logger.error(f"Discogs search error: {str(e)}")

        return results_added

    async def _search_ebay(
        self,
        db: AsyncSession,
        search: SavedSearch,
        user_id: str,
        collection_releases: set[Any],
        wantlist_releases: set[Any],
    ) -> int:
        results_added = 0

        try:
            async with EbayService() as service:
                credentials = await service.get_api_credentials(db, UUID(user_id))
                if not credentials:
                    logger.warning(f"No eBay credentials for user {user_id}")
                    return 0

                items = await service.search(search.query, search.filters, credentials)

                for item in items:
                    # Check if we already have this result
                    existing = await db.execute(
                        select(SearchResult).where(
                            SearchResult.search_id == search.id,
                            SearchResult.item_id == str(item["id"]),
                            SearchResult.platform == SearchPlatform.EBAY,
                        )
                    )
                    existing_result = existing.scalar()
                    if existing_result:
                        # Update price history if price changed
                        current_price = item.get("price", 0)
                        if existing_result.item_data.get("price") != current_price:
                            price_history = PriceHistory(
                                item_id=str(item["id"]),
                                platform=SearchPlatform.EBAY,
                                price=current_price,
                                currency=item.get("currency", "USD"),
                            )
                            db.add(price_history)
                            existing_result.item_data = item
                        continue

                    # Create search result
                    result = SearchResult(
                        search_id=search.id,
                        platform=SearchPlatform.EBAY,
                        item_id=str(item["id"]),
                        item_data=item,
                        # eBay items won't match Discogs collection
                        is_in_collection=False,
                        is_in_wantlist=False,
                    )
                    db.add(result)

                    # Add initial price history
                    price_history = PriceHistory(
                        item_id=str(item["id"]),
                        platform=SearchPlatform.EBAY,
                        price=item.get("price", 0),
                        currency=item.get("currency", "USD"),
                    )
                    db.add(price_history)

                    results_added += 1

        except Exception as e:
            logger.error(f"eBay search error: {str(e)}")

        return results_added


class SyncCollectionTask(AsyncTask):
    async def async_run(self, user_id: str) -> None:
        logger.info(f"Syncing collection for user {user_id}")
        async with AsyncSessionLocal() as db:
            try:
                async with DiscogsService() as service:
                    credentials = await service.get_api_credentials(db, UUID(user_id))
                    if not credentials:
                        logger.warning(f"No Discogs credentials for user {user_id}")
                        return

                    # Sync collection
                    collection_items = await service.sync_collection(credentials)
                    collection_added = 0
                    collection_updated = 0

                    for item in collection_items:
                        release_id = item["basic_information"]["id"]

                        # Check if already in collection
                        existing = await db.execute(
                            select(Collection).where(
                                Collection.user_id == UUID(user_id),
                                Collection.discogs_data["release_id"].as_string() == str(release_id),
                            )
                        )
                        existing_item = existing.scalar()

                        if existing_item:
                            # Update existing
                            existing_item.discogs_data = {
                                "release_id": release_id,
                                "instance_id": item["instance_id"],
                                "date_added": item["date_added"],
                                "basic_information": item["basic_information"],
                                "notes": item.get("notes", ""),
                                "rating": item.get("rating", 0),
                            }
                            collection_updated += 1
                        else:
                            # Add new
                            collection_item = Collection(
                                user_id=UUID(user_id),
                                discogs_data={
                                    "release_id": release_id,
                                    "instance_id": item["instance_id"],
                                    "date_added": item["date_added"],
                                    "basic_information": item["basic_information"],
                                    "notes": item.get("notes", ""),
                                    "rating": item.get("rating", 0),
                                },
                            )
                            db.add(collection_item)
                            collection_added += 1

                    # Sync wantlist
                    wantlist_items = await service.sync_wantlist(credentials)
                    wantlist_added = 0
                    wantlist_updated = 0

                    for item in wantlist_items:
                        release_id = item["basic_information"]["id"]

                        # Check if already in wantlist
                        existing = await db.execute(
                            select(WantList).where(
                                WantList.user_id == UUID(user_id),
                                WantList.discogs_data["release_id"].as_string() == str(release_id),
                            )
                        )
                        existing_item = existing.scalar()

                        if existing_item:
                            # Update existing
                            existing_item.discogs_data = {
                                "release_id": release_id,
                                "date_added": item["date_added"],
                                "basic_information": item["basic_information"],
                                "notes": item.get("notes", ""),
                                "rating": item.get("rating", 0),
                            }
                            wantlist_updated += 1
                        else:
                            # Add new
                            wantlist_item = WantList(
                                user_id=UUID(user_id),
                                discogs_data={
                                    "release_id": release_id,
                                    "date_added": item["date_added"],
                                    "basic_information": item["basic_information"],
                                    "notes": item.get("notes", ""),
                                    "rating": item.get("rating", 0),
                                },
                            )
                            db.add(wantlist_item)
                            wantlist_added += 1

                    await db.commit()

                    logger.info(
                        f"Collection sync for user {user_id} completed. "
                        f"Collection: {collection_added} added, "
                        f"{collection_updated} updated. "
                        f"Wantlist: {wantlist_added} added, "
                        f"{wantlist_updated} updated."
                    )
            except Exception as e:
                logger.error(f"Error syncing collection for user {user_id}: {str(e)}")
                await db.rollback()
                raise


# Create a thread-local event loop for async tasks
_thread_local = threading.local()


def get_or_create_eventloop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        if not hasattr(_thread_local, "loop"):
            _thread_local.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_thread_local.loop)
        return _thread_local.loop


# Register tasks with Celery
@celery_app.task(name="src.workers.tasks.RunSearchTask")
def run_search_task(search_id: str, user_id: str) -> None:
    """Run a search task asynchronously."""
    loop = get_or_create_eventloop()
    task = RunSearchTask()
    loop.run_until_complete(task.async_run(search_id, user_id))


@celery_app.task(name="src.workers.tasks.SyncCollectionTask")
def sync_collection_task(user_id: str) -> None:
    """Sync a user's collection asynchronously."""
    loop = get_or_create_eventloop()
    task = SyncCollectionTask()
    loop.run_until_complete(task.async_run(user_id))
