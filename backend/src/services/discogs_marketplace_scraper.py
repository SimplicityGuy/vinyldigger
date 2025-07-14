"""
Discogs Marketplace Scraper

This module provides web scraping functionality for the Discogs marketplace,
since there is no official marketplace search API. It replicates the functionality
of the NodeJS library: https://github.com/KirianCaumes/Discogs-Marketplace-API-NodeJS

The scraper uses Playwright to automate browser interactions and extract
marketplace listing data directly from the Discogs website.
"""

import asyncio
import time
from typing import Any
from urllib.parse import urlencode

from playwright.async_api import Browser, Playwright, async_playwright

from src.core.logging import get_logger
from src.core.scraper_config import get_scraper_config
from src.services.scraper_monitoring import scraper_monitor

logger = get_logger(__name__)


class DiscogsMarketplaceScraper:
    """Web scraper for Discogs marketplace listings."""

    BASE_URL = "https://www.discogs.com"
    MARKETPLACE_URL = f"{BASE_URL}/sell/list"

    def __init__(self) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.last_request_time: float = 0.0

        # Load configuration
        self.config = get_scraper_config()

    async def __aenter__(self) -> "DiscogsMarketplaceScraper":
        """Initialize the scraper with Playwright."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920x1080",
            ],
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.config.min_request_interval:
            sleep_time = self.config.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def search_marketplace(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Search Discogs marketplace for vinyl records.

        Args:
            query: Search query string
            filters: Search filters (condition, genre, format, etc.)
            page: Page number for pagination
            limit: Number of results per page (25, 50, 100, 250)

        Returns:
            Dict containing:
            - items: List of marketplace listings
            - total: Total number of results
            - page: Current page info
            - url_generated: The URL that was scraped
        """
        if not self.browser:
            raise RuntimeError("Scraper not initialized. Use async with context.")

        filters = filters or {}

        # Construct marketplace search URL
        search_url = self._build_search_url(query, filters, page, limit)

        # Record request start time for monitoring
        start_time = await scraper_monitor.record_request_start()

        # Implement retry logic
        for attempt in range(self.config.max_retries):
            try:
                # Enforce rate limiting
                await self._enforce_rate_limit()

                logger.info(
                    f"Scraping Discogs marketplace (attempt {attempt + 1}/{self.config.max_retries}): {search_url}"
                )

                # Create a new page
                page_obj = await self.browser.new_page()

                # Set user agent to appear more like a real browser
                await page_obj.set_extra_http_headers(
                    {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                )

                # Block unnecessary resources to speed up scraping
                if self.config.block_resources:
                    await page_obj.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())

                # Navigate to search URL
                await page_obj.goto(search_url, wait_until="domcontentloaded", timeout=self.config.page_load_timeout)

                # Wait for search results to load with multiple possible selectors
                try:
                    # First wait for the page container
                    await page_obj.wait_for_selector("#pjax_container", timeout=5000)
                    # Then wait for either results table or no results message
                    await page_obj.wait_for_selector(
                        "table.table_block, .no_results, .mpitems", timeout=self.config.selector_timeout
                    )
                except Exception as e:
                    logger.warning(f"Timeout waiting for marketplace content, continuing anyway: {e}")

                # Extract data using JavaScript in the browser context
                result = await page_obj.evaluate(self._extract_marketplace_data_js())

                await page_obj.close()

                # Check if we got any meaningful results
                items = result.get("items", [])
                total = result.get("total", 0)

                # Log warning if no results found
                if not items and total == 0:
                    logger.warning(f"No marketplace results found for query: {query}")

                # Record successful request
                await scraper_monitor.record_request_success(start_time=start_time, items_count=len(items), query=query)

                # Success - return results
                return {
                    "items": items,
                    "total": total,
                    "page": {"current": page, "limit": limit, "total_pages": self._calculate_total_pages(total, limit)},
                    "url_generated": search_url,
                }

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")

                # Clean up the page if it exists
                if "page_obj" in locals():
                    try:
                        await page_obj.close()
                    except Exception:
                        pass

                # If this was the last attempt, return error
                if attempt == self.config.max_retries - 1:
                    logger.error(f"All {self.config.max_retries} attempts failed for query: {query}")

                    # Record failure for monitoring
                    await scraper_monitor.record_request_failure(
                        start_time=start_time, error=str(e), error_type="scraping_failed", query=query
                    )

                    return {
                        "items": [],
                        "total": 0,
                        "page": {"current": page, "limit": limit, "total_pages": 0},
                        "url_generated": search_url,
                        "error": str(e),
                        "error_type": "scraping_failed",
                    }

                # Wait before retrying
                logger.info(f"Waiting {self.config.retry_delay} seconds before retry...")
                await asyncio.sleep(self.config.retry_delay)

        # This should never be reached, but just in case
        return {
            "items": [],
            "total": 0,
            "page": {"current": page, "limit": limit, "total_pages": 0},
            "url_generated": search_url,
            "error": "Unexpected error: no attempts succeeded",
            "error_type": "scraping_failed",
        }

    def _build_search_url(self, query: str, filters: dict[str, Any], page: int, limit: int) -> str:
        """Build the marketplace search URL with parameters."""
        params = {
            "q": query,
            "sort": filters.get("sort", "Listed,Newest"),
            "limit": str(limit),
            "page": str(page),
        }

        # Add format filter (default to Vinyl)
        if "format" in filters:
            params["format"] = filters["format"]
        else:
            params["format"] = "Vinyl"

        # Add condition filters
        if "condition" in filters and filters["condition"]:
            params["condition"] = filters["condition"]

        # Add genre filter
        if "genre" in filters and filters["genre"]:
            params["genre"] = filters["genre"]

        # Add style filter
        if "style" in filters and filters["style"]:
            if isinstance(filters["style"], list):
                for style in filters["style"]:
                    params["style[]"] = style
            else:
                params["style"] = filters["style"]

        # Add year range
        if "year_from" in filters:
            year_range = str(filters["year_from"])
            if "year_to" in filters:
                year_range += f"-{filters['year_to']}"
            params["year"] = year_range
        elif "year_to" in filters:
            params["year"] = f"-{filters['year_to']}"

        # Add price range
        if "price_min" in filters and filters["price_min"]:
            params["pricerange"] = f"{filters['price_min']}-{filters.get('price_max', '')}"
        elif "price_max" in filters and filters["price_max"]:
            params["pricerange"] = f"-{filters['price_max']}"

        # Add currency
        if "currency" in filters and filters["currency"]:
            params["currency"] = filters["currency"]
        else:
            params["currency"] = "USD"

        # Add seller country filter
        if "seller_location_preference" in filters and filters["seller_location_preference"]:
            if filters["seller_location_preference"] != "ANY":
                params["ships_from"] = filters["seller_location_preference"]

        return f"{self.MARKETPLACE_URL}?{urlencode(params, doseq=True)}"

    def _extract_marketplace_data_js(self) -> str:
        """JavaScript code to extract marketplace listing data from the page."""
        return """
        () => {
            // Helper function to safely parse floats
            function safeParseFloat(text) {
                if (!text) return 0.0;
                const cleaned = text.replace(/[^0-9.]/g, '');
                return cleaned ? parseFloat(cleaned) : 0.0;
            }

            // Helper function to safely parse integers
            function safeParseInt(text) {
                if (!text) return 0;
                const cleaned = text.replace(/[^0-9]/g, '');
                return cleaned ? parseInt(cleaned, 10) : 0;
            }

            // Helper function to clean text
            function cleanText(text) {
                return text ? text.trim() : '';
            }

            // Extract total number of results
            let total = 0;
            const paginationEl = document.querySelector('.pagination_total');
            if (paginationEl) {
                const totalMatch = paginationEl.textContent.match(/of\\s+([0-9,]+)/);
                if (totalMatch) {
                    total = parseInt(totalMatch[1].replace(/,/g, ''), 10);
                }
            }

            // Extract marketplace listings
            const listings = [];
            const rows = document.querySelectorAll('table.table_block tbody tr.shortcut_navigable');

            rows.forEach((row, index) => {
                try {
                    // Get the main cells - structure is:
                    // 0: item_picture, 1: item_description, 2: seller_info,
                    // 3: mobile-description, 4: item_price, 5: add_to_cart
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 5) return;

                    // === TITLE AND RELEASE INFO ===
                    const titleLink = cells[1].querySelector('.item_description_title');
                    const titleText = titleLink ? cleanText(titleLink.textContent) : '';
                    const itemUrl = titleLink ? titleLink.href : '';

                    // Extract listing ID from URL (it's after /item/)
                    const listingMatch = itemUrl.match(/\\/item\\/(\\d+)/);
                    const listingId = listingMatch ? listingMatch[1] : (Date.now() + index).toString();

                    // Extract release ID from the release link if available
                    const releaseLink = cells[1].querySelector('a.item_release_link');
                    let releaseId = null;
                    if (releaseLink) {
                        const releaseMatch = releaseLink.href.match(/\\/release\\/(\\d+)/);
                        releaseId = releaseMatch ? releaseMatch[1] : null;
                    }

                    // Parse artist and album from title
                    let artist = '';
                    let album = titleText;
                    // Match various dash types and formats like "Artist - Album (Format)"
                    const titleMatch = titleText.match(/^(.+?)\\s*[-–—]\\s*(.+?)(?:\\s*\\([^)]+\\))?$/);
                    if (titleMatch) {
                        artist = cleanText(titleMatch[1]);
                        album = cleanText(titleMatch[2]);
                    }

                    // Extract label and catalog number
                    const labelEl = cells[1].querySelector('.label_and_cat a');
                    const label = labelEl ? cleanText(labelEl.textContent) : '';
                    const catnoEl = cells[1].querySelector('.item_catno');
                    const catno = catnoEl ? cleanText(catnoEl.textContent) : '';

                    // === CONDITION INFO ===
                    const conditionEl = cells[1].querySelector('.item_condition');
                    let mediaCondition = '';
                    let sleeveCondition = '';

                    if (conditionEl) {
                        // Get all spans (not just labeled ones)
                        const allSpans = conditionEl.querySelectorAll('span');

                        // The structure is usually:
                        // span[0]: "Media Condition:" (desktop label)
                        // span[1]: "Media:" (mobile label)
                        // span[2]: The actual media condition
                        // span[3]: Tooltip trigger
                        // span[4]: "Sleeve Condition:" (desktop label)
                        // span[5]: "Sleeve:" (mobile label)
                        // span[6]: The actual sleeve condition

                        if (allSpans.length >= 3) {
                            // Extract media condition from span[2]
                            const mediaText = allSpans[2] ? cleanText(allSpans[2].textContent) : '';
                            // Extract just the condition grade (before any newline)
                            const mediaMatch = mediaText.match(/^([^\\n]+)/);
                            mediaCondition = mediaMatch ? cleanText(mediaMatch[1]) : mediaText;
                        }

                        if (allSpans.length >= 9) {
                            // Extract sleeve condition from span[8] (after sleeve labels)
                            const sleeveText = allSpans[8] ? cleanText(allSpans[8].textContent) : '';
                            // Extract just the condition grade (before any newline)
                            const sleeveMatch = sleeveText.match(/^([^\\n]+)/);
                            sleeveCondition = sleeveMatch ? cleanText(sleeveMatch[1]) : sleeveText;
                        }
                    }

                    // === SELLER INFO ===
                    const sellerLink = cells[2].querySelector('a');
                    const sellerName = sellerLink ? cleanText(sellerLink.textContent) : '';
                    const sellerUrl = sellerLink ? sellerLink.href : '';
                    // Extract seller ID from URL - it's after /seller/
                    const sellerIdMatch = sellerUrl.match(/\\/seller\\/([^/?]+)/);
                    const sellerId = sellerIdMatch ? sellerIdMatch[1] : '';

                    // Extract rating - it's in the text after the seller name
                    const sellerText = cells[2].textContent || '';
                    const ratingMatch = sellerText.match(/([0-9.]+)%/);
                    const sellerRating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;

                    // === PRICE INFO ===
                    const priceCell = cells[4];
                    const priceEl = priceCell.querySelector('span.price');
                    let price = 0;
                    let currency = 'USD';
                    let shippingPrice = null;

                    if (priceEl) {
                        const priceText = cleanText(priceEl.textContent);
                        // Handle different currency formats
                        const priceMatch = priceText.match(/([€£$¥])?\\s*([0-9,]+\\.?[0-9]*)/);
                        if (priceMatch) {
                            // Map currency symbols
                            const currencyMap = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY'};
                            if (priceMatch[1]) {
                                currency = currencyMap[priceMatch[1]] || 'USD';
                            }
                            price = parseFloat(priceMatch[2].replace(/,/g, ''));
                        }
                    }

                    // Check for shipping cost (usually after price)
                    const priceText = priceCell.textContent || '';
                    const shippingMatch = priceText.match(/\\+[€£$¥]?\\s*([0-9,]+\\.?[0-9]*)/);
                    if (shippingMatch) {
                        shippingPrice = parseFloat(shippingMatch[1].replace(/,/g, ''));
                    }

                    // Extract community information (have/want counts)
                    const communityEl = cells[1].querySelector('.community_summary');
                    let haveCount = 0;
                    let wantCount = 0;
                    if (communityEl) {
                        const haveEl = communityEl.querySelector('.have_indicator');
                        const wantEl = communityEl.querySelector('.want_indicator');
                        if (haveEl) {
                            const haveMatch = haveEl.textContent.match(/\\d+/);
                            haveCount = haveMatch ? parseInt(haveMatch[0]) : 0;
                        }
                        if (wantEl) {
                            const wantMatch = wantEl.textContent.match(/\\d+/);
                            wantCount = wantMatch ? parseInt(wantMatch[0]) : 0;
                        }
                    }

                    // Extract image URL
                    const imageEl = cells[0].querySelector('img');
                    const imageUrl = imageEl ? imageEl.src : '';

                    // Extract format information
                    const formatEl = cells[1].querySelector('.item_release_format');
                    const formats = formatEl ? [cleanText(formatEl.textContent)] : ['Vinyl'];

                    // Extract year if available
                    let year = null;
                    const yearMatch = titleText.match(/\\((\\d{4})\\)/);
                    if (yearMatch) {
                        year = parseInt(yearMatch[1]);
                    }

                    // Create the listing object
                    const listing = {
                        id: listingId,
                        title: titleText,
                        artist: artist,
                        album: album,
                        year: year,
                        format: formats,
                        label: label ? [label] : [],
                        catno: catno,
                        condition: mediaCondition,
                        sleeve_condition: sleeveCondition,
                        price: price,
                        currency: currency,
                        shipping_price: shippingPrice,
                        seller: {
                            id: sellerId,
                            username: sellerName,
                            rating: sellerRating,
                            url: sellerUrl
                        },
                        community: {
                            have: haveCount,
                            want: wantCount
                        },
                        image_url: imageUrl,
                        item_url: itemUrl,
                        // Additional fields for compatibility
                        release_id: releaseId,
                        listing_id: listingId,
                        thumb: imageUrl,
                        cover_image: imageUrl,
                        resource_url: itemUrl,
                        uri: itemUrl,
                        location: '', // Could extract from seller info if needed
                        posted: '', // Could extract from listing date if available
                        allow_offers: false,
                        status: 'For Sale',
                        ships_from: '' // Could extract from seller location if available
                    };

                    listings.push(listing);
                } catch (error) {
                    console.error('Error parsing listing:', error);
                }
            });

            return {
                items: listings,
                total: total
            };
        }
        """

    def _calculate_total_pages(self, total_items: int, limit: int) -> int:
        """Calculate total number of pages based on total items and limit."""
        if total_items <= 0 or limit <= 0:
            return 0
        return (total_items + limit - 1) // limit  # Ceiling division

    async def get_marketplace_listing_details(self, listing_id: str) -> dict[str, Any] | None:
        """
        Get detailed information for a specific marketplace listing.

        Args:
            listing_id: The listing ID to get details for

        Returns:
            Dict with detailed listing information or None if not found
        """
        if not self.browser:
            raise RuntimeError("Scraper not initialized. Use async with context.")

        listing_url = f"{self.BASE_URL}/sell/item/{listing_id}"

        try:
            page = await self.browser.new_page()
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=self.config.page_load_timeout)

            # Extract detailed listing information
            result = await page.evaluate("""
                () => {
                    // Extract detailed listing data
                    const titleElement = document.querySelector('h1.item_title');
                    const title = titleElement ? titleElement.textContent.trim() : '';

                    const priceElement = document.querySelector('.price');
                    const priceText = priceElement ? priceElement.textContent.trim() : '';

                    return {
                        id: window.location.pathname.split('/').pop(),
                        title: title,
                        price_text: priceText
                    };
                }
            """)

            await page.close()
            return result

        except Exception as e:
            logger.error(f"Error getting listing details for {listing_id}: {str(e)}")
            return None


# Utility function to create and use the scraper
async def search_discogs_marketplace(
    query: str, filters: dict[str, Any] | None = None, page: int = 1, limit: int = 50
) -> dict[str, Any]:
    """
    Convenience function to search Discogs marketplace.

    Args:
        query: Search query string
        filters: Search filters
        page: Page number
        limit: Results per page

    Returns:
        Search results dict
    """
    async with DiscogsMarketplaceScraper() as scraper:
        return await scraper.search_marketplace(query, filters, page, limit)


if __name__ == "__main__":
    # Test the scraper
    async def test_scraper():
        results = await search_discogs_marketplace(
            "Pink Floyd Dark Side of the Moon",
            {"format": "Vinyl", "condition": "Near Mint (NM or M-)"},
            page=1,
            limit=25,
        )
        print(f"Found {results['total']} results")
        for item in results["items"][:3]:  # Show first 3 items
            print(f"- {item['artist']} - {item['album']} ({item['condition']}) - {item['price']} {item['currency']}")

    asyncio.run(test_scraper())
