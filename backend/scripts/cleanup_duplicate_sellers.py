#!/usr/bin/env python3
"""Clean up duplicate sellers in the database.

This script identifies duplicate sellers (same platform + platform_seller_id)
and merges them by:
1. Keeping the most recent seller record
2. Updating all foreign key references to point to the kept record
3. Deleting the duplicate records
4. Adding a unique constraint to prevent future duplicates
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.config import settings
from src.core.logging import get_logger
from src.models.search import SearchResult
from src.models.seller import Seller

logger = get_logger(__name__)


async def cleanup_duplicate_sellers():
    """Clean up duplicate sellers and add unique constraint."""

    # Create async engine
    engine = create_async_engine(str(settings.database_url))

    async with AsyncSession(engine) as db:
        try:
            # Find all duplicate seller groups
            logger.info("Finding duplicate sellers...")

            duplicate_query = text("""
                SELECT platform, platform_seller_id, array_agg(id ORDER BY created_at DESC) as seller_ids
                FROM sellers
                GROUP BY platform, platform_seller_id
                HAVING COUNT(*) > 1
            """)

            result = await db.execute(duplicate_query)
            duplicate_groups = result.fetchall()

            logger.info(f"Found {len(duplicate_groups)} duplicate seller groups")

            total_deleted = 0

            for group in duplicate_groups:
                platform, platform_seller_id, seller_ids = group

                # Keep the first (most recent) seller, delete the rest
                keep_seller_id = seller_ids[0]  # Already a UUID object
                delete_seller_ids = seller_ids[1:]  # Already UUID objects

                seller_key = f"{platform}:{platform_seller_id}"
                duplicate_count = len(delete_seller_ids)
                logger.info(
                    f"Processing {seller_key} - keeping {keep_seller_id}, deleting {duplicate_count} duplicates"
                )

                # Update all search_results to point to the kept seller
                for delete_id in delete_seller_ids:
                    await db.execute(
                        update(SearchResult).where(SearchResult.seller_id == delete_id).values(seller_id=keep_seller_id)
                    )

                # Delete the duplicate sellers
                await db.execute(delete(Seller).where(Seller.id.in_(delete_seller_ids)))

                total_deleted += len(delete_seller_ids)

            # Commit the changes
            await db.commit()
            logger.info(f"Successfully deleted {total_deleted} duplicate sellers")

            # Add unique constraint to prevent future duplicates
            logger.info("Adding unique constraint...")
            await db.execute(
                text("""
                ALTER TABLE sellers
                ADD CONSTRAINT unique_platform_seller_id
                UNIQUE (platform, platform_seller_id)
            """)
            )
            await db.commit()
            logger.info("Added unique constraint: unique_platform_seller_id")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await db.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicate_sellers())
