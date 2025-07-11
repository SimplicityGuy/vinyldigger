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
from src.models.collection_item import CollectionItem, WantListItem
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
                collection_result = await db.execute(select(Collection).where(Collection.user_id == UUID(user_id)))
                collections = collection_result.scalars().all()

                collection_releases = set()
                for collection in collections:
                    items_result = await db.execute(
                        select(CollectionItem).where(CollectionItem.collection_id == collection.id)
                    )
                    for item in items_result.scalars():
                        if item.item_metadata and "release_id" in item.item_metadata:
                            collection_releases.add(str(item.item_metadata["release_id"]))
                        elif item.platform_item_id:
                            collection_releases.add(item.platform_item_id)

                wantlist_result = await db.execute(select(WantList).where(WantList.user_id == UUID(user_id)))
                wantlists = wantlist_result.scalars().all()

                wantlist_releases = set()
                for wantlist in wantlists:
                    items_result = await db.execute(
                        select(WantListItem).where(WantListItem.want_list_id == wantlist.id)
                    )
                    for item in items_result.scalars():
                        if item.item_metadata and "release_id" in item.item_metadata:
                            wantlist_releases.add(str(item.item_metadata["release_id"]))
                        elif item.platform_item_id:
                            wantlist_releases.add(item.platform_item_id)

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

                # Update last_run_at
                search.last_run_at = datetime.utcnow()
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
                items = await service.search(search.query, search.filters, db, user_id)

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
                    # Sync collection
                    collection_items = await service.sync_collection(db, user_id)
                    collection_added = 0
                    collection_updated = 0

                    # Get or create collection for this user and platform
                    collection_result = await db.execute(
                        select(Collection).where(
                            Collection.user_id == UUID(user_id),
                            Collection.platform == SearchPlatform.DISCOGS,
                        )
                    )
                    collection = collection_result.scalar_one_or_none()

                    if not collection:
                        collection = Collection(
                            user_id=UUID(user_id),
                            platform=SearchPlatform.DISCOGS,
                            item_count=0,
                        )
                        db.add(collection)
                        await db.flush()

                    for item in collection_items:
                        release_id = item["basic_information"]["id"]
                        basic_info = item["basic_information"]

                        # Check if already in collection
                        existing = await db.execute(
                            select(CollectionItem).where(
                                CollectionItem.collection_id == collection.id,
                                CollectionItem.platform_item_id == str(release_id),
                            )
                        )
                        existing_item = existing.scalar_one_or_none()

                        if existing_item:
                            # Update existing
                            existing_item.title = basic_info.get("title", "Unknown")
                            existing_item.artist = ", ".join([a["name"] for a in basic_info.get("artists", [])])
                            existing_item.year = basic_info.get("year")
                            existing_item.format = ", ".join([f.get("name", "") for f in basic_info.get("formats", [])])
                            existing_item.label = ", ".join([label["name"] for label in basic_info.get("labels", [])])
                            existing_item.catalog_number = basic_info.get("catno", "")
                            existing_item.item_metadata = {
                                "release_id": release_id,
                                "instance_id": item["instance_id"],
                                "date_added": item["date_added"],
                                "basic_information": basic_info,
                                "notes": item.get("notes", ""),
                                "rating": item.get("rating", 0),
                            }
                            collection_updated += 1
                        else:
                            # Add new
                            collection_item = CollectionItem(
                                collection_id=collection.id,
                                platform_item_id=str(release_id),
                                title=basic_info.get("title", "Unknown"),
                                artist=", ".join([a["name"] for a in basic_info.get("artists", [])]),
                                year=basic_info.get("year"),
                                format=", ".join([f.get("name", "") for f in basic_info.get("formats", [])]),
                                label=", ".join([label["name"] for label in basic_info.get("labels", [])]),
                                catalog_number=basic_info.get("catno", ""),
                                item_metadata={
                                    "release_id": release_id,
                                    "instance_id": item["instance_id"],
                                    "date_added": item["date_added"],
                                    "basic_information": basic_info,
                                    "notes": item.get("notes", ""),
                                    "rating": item.get("rating", 0),
                                },
                                added_at=datetime.utcnow(),
                            )
                            db.add(collection_item)
                            collection_added += 1

                    # Update collection item count
                    collection.item_count = collection_added + collection_updated
                    collection.last_sync_at = datetime.utcnow()

                    # Sync wantlist
                    wantlist_items = await service.sync_wantlist(db, user_id)
                    wantlist_added = 0
                    wantlist_updated = 0

                    # Get or create wantlist for this user and platform
                    wantlist_result = await db.execute(
                        select(WantList).where(
                            WantList.user_id == UUID(user_id),
                            WantList.platform == SearchPlatform.DISCOGS,
                        )
                    )
                    wantlist = wantlist_result.scalar_one_or_none()

                    if not wantlist:
                        wantlist = WantList(
                            user_id=UUID(user_id),
                            platform=SearchPlatform.DISCOGS,
                            item_count=0,
                        )
                        db.add(wantlist)
                        await db.flush()

                    for item in wantlist_items:
                        release_id = item["basic_information"]["id"]
                        basic_info = item["basic_information"]

                        # Check if already in wantlist
                        existing = await db.execute(
                            select(WantListItem).where(
                                WantListItem.want_list_id == wantlist.id,
                                WantListItem.platform_item_id == str(release_id),
                            )
                        )
                        existing_item = existing.scalar_one_or_none()

                        if existing_item:
                            # Update existing
                            existing_item.title = basic_info.get("title", "Unknown")
                            existing_item.artist = ", ".join([a["name"] for a in basic_info.get("artists", [])])
                            existing_item.year = basic_info.get("year")
                            existing_item.format = ", ".join([f.get("name", "") for f in basic_info.get("formats", [])])
                            existing_item.item_metadata = {
                                "release_id": release_id,
                                "date_added": item["date_added"],
                                "basic_information": basic_info,
                                "notes": item.get("notes", ""),
                                "rating": item.get("rating", 0),
                            }
                            wantlist_updated += 1
                        else:
                            # Add new
                            wantlist_item = WantListItem(
                                want_list_id=wantlist.id,
                                platform_item_id=str(release_id),
                                title=basic_info.get("title", "Unknown"),
                                artist=", ".join([a["name"] for a in basic_info.get("artists", [])]),
                                year=basic_info.get("year"),
                                format=", ".join([f.get("name", "") for f in basic_info.get("formats", [])]),
                                notes=item.get("notes", ""),
                                item_metadata={
                                    "release_id": release_id,
                                    "date_added": item["date_added"],
                                    "basic_information": basic_info,
                                    "notes": item.get("notes", ""),
                                    "rating": item.get("rating", 0),
                                },
                                added_at=datetime.utcnow(),
                            )
                            db.add(wantlist_item)
                            wantlist_added += 1

                    # Update wantlist item count
                    wantlist.item_count = wantlist_added + wantlist_updated
                    wantlist.last_sync_at = datetime.utcnow()

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


def get_or_create_eventloop() -> asyncio.AbstractEventLoop:
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
