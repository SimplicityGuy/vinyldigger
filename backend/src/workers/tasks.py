"""Background tasks for VinylDigger.

ANALYSIS EXECUTION MODEL:
- Analysis is EVENT-DRIVEN: runs automatically after each search execution
- Analysis frequency = Search frequency (user configurable via check_interval_hours)
- Default: Every 24 hours per saved search
- Manual: Users can trigger immediate searches anytime

SEARCH → ANALYSIS FLOW:
1. Scheduler (hourly) → Checks SavedSearch.check_interval_hours
2. RunSearchTask → Executes search across platforms
3. Analysis runs immediately → Item matching, seller analysis, recommendations
4. Results cached → Available via /api/v1/analysis/... endpoints until next run
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from celery import Task
from celery.app.task import Task as CeleryTask
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.logging import get_logger
from src.models.collection import Collection, WantList
from src.models.collection_item import CollectionItem, WantListItem
from src.models.price_history import PriceHistory
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.services.discogs import DiscogsService
from src.services.ebay import EbayService
from src.services.item_matcher import ItemMatchingService
from src.services.recommendation_engine import RecommendationEngine
from src.services.seller_analyzer import SellerAnalysisService
from src.workers.celery_app import celery_app

# Enable generic type parameters for Celery Tasks after imports
CeleryTask.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)  # type: ignore[attr-defined]

logger = get_logger(__name__)


class AsyncTask(Task):  # type: ignore[type-arg]  # celery-types incomplete generic support
    """Base class for async Celery tasks."""

    def run(self, *args: Any, **kwargs: Any) -> Any:
        # Use asyncio.run() to create a fresh event loop for each task
        # This ensures proper greenlet context for async SQLAlchemy operations
        # and avoids issues with thread-local event loops in Celery workers
        return asyncio.run(self.async_run(*args, **kwargs))

    async def async_run(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class RunSearchTask(AsyncTask):
    def __init__(self) -> None:
        super().__init__()
        self.item_matcher = ItemMatchingService()
        self.seller_analyzer = SellerAnalysisService()
        self.recommendation_engine = RecommendationEngine()

    async def async_run(self, search_id: str, user_id: str) -> None:
        logger.info(f"Running enhanced search {search_id} for user {user_id}")

        # Create a fresh async engine and session for this worker task
        # Using asyncio.run() ensures proper greenlet context for SQLAlchemy
        worker_engine = create_async_engine(str(settings.database_url))

        WorkerAsyncSession = async_sessionmaker(
            worker_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Disable autoflush to prevent implicit flushes that can trigger lazy loading
        )

        async with WorkerAsyncSession() as db:
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
                        elif item.item_id:
                            collection_releases.add(item.item_id)

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
                        elif item.item_id:
                            wantlist_releases.add(item.item_id)

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

                # Flush and commit search results before analysis
                await db.flush()
                await db.commit()

                # Run enhanced analysis if we have new results
                if results_added > 0:
                    logger.info(f"Running analysis for {results_added} new results in search {search_id}")

                    # Perform item matching and seller analysis
                    await self._perform_item_matching(db, search_id)
                    await self._perform_seller_analysis(db, search_id)

                    # Generate recommendations
                    await self._generate_recommendations(db, search_id, user_id)

                    # Flush before commit to ensure all changes are written
                    await db.flush()
                    await db.commit()
                    logger.info(f"Analysis completed for search {search_id}")

                # Update last_run_at
                search.last_run_at = datetime.now(UTC)
                await db.flush()
                await db.commit()

                logger.info(f"Search {search_id} completed successfully. Added {results_added} new results.")
            except Exception as e:
                logger.error(f"Error running search {search_id}: {str(e)}")
                await db.rollback()
                raise
            finally:
                # Clean up the worker engine
                await worker_engine.dispose()

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
                    # For marketplace listings, use listing ID as item_id to avoid duplicates
                    listing_id = str(item["id"])
                    release_id = str(item.get("release_id", item.get("id")))

                    # Check if we already have this result
                    existing = await db.execute(
                        select(SearchResult).where(
                            SearchResult.search_id == search.id,
                            SearchResult.item_id == listing_id,
                            SearchResult.platform == SearchPlatform.DISCOGS,
                        )
                    )
                    if existing.scalar():
                        continue

                    # Extract seller information and create/update seller
                    seller_info = await self.seller_analyzer.extract_seller_info(item, SearchPlatform.DISCOGS)
                    seller = await self.seller_analyzer.find_or_create_seller(db, SearchPlatform.DISCOGS, seller_info)

                    # Extract item information for pricing and condition
                    item_info = self.item_matcher.extract_item_info(item, "discogs")

                    # Check collection/wantlist using release_id (not listing_id)
                    is_in_collection = release_id in collection_releases
                    is_in_wantlist = release_id in wantlist_releases

                    # Create search result with enhanced data
                    result = SearchResult(
                        search_id=search.id,
                        platform=SearchPlatform.DISCOGS,
                        item_id=listing_id,  # Use listing ID for uniqueness
                        item_data=item,
                        is_in_collection=is_in_collection,
                        is_in_wantlist=is_in_wantlist,
                        seller_id=seller.id,
                        item_price=Decimal(str(item_info.get("price", 0))) if item_info.get("price") else None,
                        item_condition=item_info.get("condition"),
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
                # Search using OAuth token or app token
                items = await service.search(search.query, search.filters, db, UUID(user_id))

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

                    # Extract seller information and create/update seller
                    seller_info = await self.seller_analyzer.extract_seller_info(item, SearchPlatform.EBAY)
                    seller = await self.seller_analyzer.find_or_create_seller(db, SearchPlatform.EBAY, seller_info)

                    # Extract item information for pricing and condition
                    item_info = self.item_matcher.extract_item_info(item, "ebay")

                    # Create search result with enhanced data
                    result = SearchResult(
                        search_id=search.id,
                        platform=SearchPlatform.EBAY,
                        item_id=str(item["id"]),
                        item_data=item,
                        # eBay items won't match Discogs collection directly
                        is_in_collection=False,
                        is_in_wantlist=False,
                        seller_id=seller.id,
                        item_price=Decimal(str(item_info.get("price", 0))) if item_info.get("price") else None,
                        item_condition=item_info.get("condition"),
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

    async def _perform_item_matching(self, db: AsyncSession, search_id: str) -> None:
        """Perform item matching for search results."""
        logger.info(f"Performing item matching for search {search_id}")

        # Get all search results that don't have item matches yet
        results_query = await db.execute(
            select(SearchResult).where(SearchResult.search_id == search_id, SearchResult.item_match_id.is_(None))
        )
        search_results = results_query.scalars().all()

        for result in search_results:
            try:
                # Perform item matching
                match_result = await self.item_matcher.match_search_result(
                    db, str(result.id), result.item_data, result.platform.value.lower()
                )

                if match_result:
                    # Update search result with item match
                    result.item_match_id = match_result.item_match_id

            except Exception as e:
                logger.error(f"Error matching item {result.id}: {str(e)}")
                continue

    async def _perform_seller_analysis(self, db: AsyncSession, search_id: str) -> None:
        """Perform seller inventory analysis for search results."""
        logger.info(f"Performing seller analysis for search {search_id}")

        # Get all sellers in this search
        sellers_query = await db.execute(
            select(SearchResult.seller_id)
            .where(SearchResult.search_id == search_id, SearchResult.seller_id.is_not(None))
            .distinct()
        )
        seller_ids = [row[0] for row in sellers_query.all()]

        for seller_id in seller_ids:
            try:
                # Create seller inventory entries
                seller_results_query = await db.execute(
                    select(SearchResult).where(SearchResult.search_id == search_id, SearchResult.seller_id == seller_id)
                )
                seller_results = seller_results_query.scalars().all()

                from src.models.seller import SellerInventory

                for result in seller_results:
                    # Check if inventory entry already exists
                    existing_inventory = await db.execute(
                        select(SellerInventory).where(
                            SellerInventory.seller_id == seller_id, SellerInventory.search_result_id == result.id
                        )
                    )

                    if not existing_inventory.scalar():
                        # Create inventory entry
                        inventory_item = SellerInventory(
                            seller_id=seller_id,
                            search_result_id=result.id,
                            item_title=result.item_data.get("title", "Unknown"),
                            item_price=result.item_price or Decimal("0.00"),
                            item_condition=result.item_condition,
                            is_in_wantlist=result.is_in_wantlist,
                            wantlist_priority=5 if result.is_in_wantlist else None,  # Default priority
                        )
                        db.add(inventory_item)

            except Exception as e:
                logger.error(f"Error analyzing seller {seller_id}: {str(e)}")
                continue

    async def _generate_recommendations(self, db: AsyncSession, search_id: str, user_id: str) -> None:
        """Generate deal recommendations for search results."""
        logger.info(f"Generating recommendations for search {search_id}")

        try:
            # Use recommendation engine to analyze results and generate recommendations
            await self.recommendation_engine.analyze_search_results(db, search_id, user_id)

            # Note: We avoid accessing returned analysis object as it has lazy-loaded relationships
            # that would trigger a database query in an async context, causing greenlet_spawn errors
            logger.info(f"Analysis completed for search {search_id}")

        except Exception as e:
            logger.error(f"Error generating recommendations for search {search_id}: {str(e)}")


class SyncCollectionTask(AsyncTask):
    async def async_run(self, user_id: str, sync_type: str = "both") -> None:
        logger.info(f"Syncing {sync_type} for user {user_id}")

        # Create a fresh async engine and session for this worker task
        worker_engine = create_async_engine(str(settings.database_url))

        WorkerAsyncSession = async_sessionmaker(
            worker_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Disable autoflush to prevent implicit flushes
        )

        async with WorkerAsyncSession() as db:
            try:
                async with DiscogsService() as service:
                    collection_added = 0
                    collection_updated = 0
                    wantlist_added = 0
                    wantlist_updated = 0

                    # Sync collection if requested
                    if sync_type in ["both", "collection"]:
                        collection_items = await service.sync_collection(db, user_id)

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
                            # Let SQLAlchemy handle flushing automatically

                        for item in collection_items:
                            release_id = item["basic_information"]["id"]
                            instance_id = item["instance_id"]
                            basic_info = item["basic_information"]

                            # Check if already in collection (use instance_id for unique identification)
                            existing = await db.execute(
                                select(CollectionItem).where(
                                    CollectionItem.collection_id == collection.id,
                                    CollectionItem.item_id == str(instance_id),
                                )
                            )
                            existing_item = existing.scalar_one_or_none()

                            if existing_item:
                                # Update existing
                                existing_item.title = basic_info.get("title", "Unknown")
                                existing_item.artist = ", ".join([a["name"] for a in basic_info.get("artists", [])])
                                existing_item.year = basic_info.get("year")
                                existing_item.format = ", ".join(
                                    [f.get("name", "") for f in basic_info.get("formats", [])]
                                )
                                existing_item.label = ", ".join(
                                    [label["name"] for label in basic_info.get("labels", [])]
                                )
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
                                    item_id=str(instance_id),
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

                    # Sync wantlist if requested
                    if sync_type in ["both", "wantlist"]:
                        wantlist_items = await service.sync_wantlist(db, user_id)

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
                            # Let SQLAlchemy handle flushing automatically

                        for item in wantlist_items:
                            release_id = item["basic_information"]["id"]
                            basic_info = item["basic_information"]

                            # Check if already in wantlist
                            existing = await db.execute(
                                select(WantListItem).where(
                                    WantListItem.want_list_id == wantlist.id,
                                    WantListItem.item_id == str(release_id),
                                )
                            )
                            existing_item = existing.scalar_one_or_none()

                            if existing_item:
                                # Update existing
                                existing_item.title = basic_info.get("title", "Unknown")
                                existing_item.artist = ", ".join([a["name"] for a in basic_info.get("artists", [])])
                                existing_item.year = basic_info.get("year")
                                existing_item.format = ", ".join(
                                    [f.get("name", "") for f in basic_info.get("formats", [])]
                                )
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
                                    item_id=str(release_id),
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

                    # Flush before commit
                    await db.flush()
                    await db.commit()

                    if sync_type == "collection":
                        logger.info(
                            f"Collection sync for user {user_id} completed. "
                            f"{collection_added} added, {collection_updated} updated."
                        )
                    elif sync_type == "wantlist":
                        logger.info(
                            f"Want list sync for user {user_id} completed. "
                            f"{wantlist_added} added, {wantlist_updated} updated."
                        )
                    else:
                        logger.info(
                            f"Collection and want list sync for user {user_id} completed. "
                            f"Collection: {collection_added} added, "
                            f"{collection_updated} updated. "
                            f"Wantlist: {wantlist_added} added, "
                            f"{wantlist_updated} updated."
                        )
            except Exception as e:
                logger.error(f"Error syncing collection for user {user_id}: {str(e)}")
                await db.rollback()
                raise
            finally:
                # Clean up the worker engine
                await worker_engine.dispose()


# Use the original task registration method
@celery_app.task(name="src.workers.tasks.RunSearchTask")
def run_search_task(search_id: str, user_id: str) -> None:
    """Run search task using the class-based approach."""
    task = RunSearchTask()
    task.run(search_id, user_id)


@celery_app.task(name="src.workers.tasks.SyncCollectionTask")
def sync_collection_task(user_id: str, sync_type: str = "both") -> None:
    """Sync a user's collection asynchronously."""
    task = SyncCollectionTask()
    task.run(user_id, sync_type)
