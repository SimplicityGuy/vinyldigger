import asyncio
from collections.abc import Generator
from typing import Any, Literal, cast
from uuid import UUID

import httpx
from httpx import AsyncClient, Request, Response
from oauthlib.oauth1 import Client as OAuth1Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models import AppConfig, OAuthProvider, OAuthToken
from src.models.api_key import APIService


class DiscogsOAuth1Auth(httpx.Auth):
    """Custom OAuth1 authentication for httpx."""

    def __init__(self, consumer_key: str, consumer_secret: str, token: str, token_secret: str):
        self.oauth_client = OAuth1Client(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=token,
            resource_owner_secret=token_secret,
            signature_method="HMAC-SHA1",
            signature_type="AUTH_HEADER",
        )

    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        """Apply OAuth1 signature to the request."""
        # Convert httpx request to a format oauthlib can work with
        uri = str(request.url)
        method = request.method
        body = request.content.decode() if request.content else None
        headers = dict(request.headers)

        # Generate OAuth signature
        # Cast to literal type expected by oauthlib
        http_method = cast(
            Literal["CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"],
            method,
        )
        uri, headers, body = self.oauth_client.sign(uri, http_method=http_method, body=body, headers=headers)

        # Update the request with OAuth headers
        request.headers.update(headers)
        yield request


class DiscogsService:
    BASE_URL = "https://api.discogs.com"

    def __init__(self) -> None:
        self.service = APIService.DISCOGS
        self.client: AsyncClient | None = None
        self.logger = get_logger(__name__)

    async def __aenter__(self) -> "DiscogsService":
        self.client = AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "User-Agent": "VinylDigger/1.0 +https://github.com/SimplicityGuy/vinyldigger",
                "Accept": "application/vnd.discogs.v2.plaintext+json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.client:
            await self.client.aclose()

    async def get_oauth_auth(self, db: AsyncSession, user_id: str) -> DiscogsOAuth1Auth | None:
        """Get OAuth1 authentication for the user."""
        # Get app configuration
        app_config_result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.DISCOGS))
        app_config = app_config_result.scalar_one_or_none()

        if not app_config:
            self.logger.error("Discogs OAuth is not configured in app settings")
            return None

        # Get user's OAuth token (most recent if multiple exist)
        token_result = await db.execute(
            select(OAuthToken)
            .where(
                OAuthToken.user_id == UUID(user_id),
                OAuthToken.provider == OAuthProvider.DISCOGS,
            )
            .order_by(OAuthToken.created_at.desc())
            .limit(1)
        )
        oauth_token = token_result.scalar_one_or_none()

        if not oauth_token:
            self.logger.error(f"User {user_id} has not authorized Discogs access")
            return None

        if not oauth_token.access_token_secret:
            self.logger.warning(f"No access token secret for user {user_id}")
            return None

        return DiscogsOAuth1Auth(
            consumer_key=app_config.consumer_key,
            consumer_secret=app_config.consumer_secret,
            token=oauth_token.access_token,
            token_secret=oauth_token.access_token_secret,
        )

    async def search(self, query: str, filters: dict[str, Any], db: AsyncSession, user_id: str) -> list[dict[str, Any]]:
        """
        Search Discogs marketplace for vinyl records.

        This method searches actual marketplace listings (items for sale) using web scraping
        since there is no official marketplace search API. It provides real prices and
        seller information from live marketplace listings.

        Args:
            query: Search query string
            filters: Search filters including condition, location, price range
            db: Database session for OAuth token retrieval (not used for scraping)
            user_id: User ID for authentication (not used for scraping)

        Returns:
            List of marketplace listing dictionaries with pricing and seller data

        Note:
            Uses web scraping via Playwright to get live listings with:
            - Actual asking prices
            - Seller information (username, rating, location)
            - Media and sleeve conditions
            - Shipping costs where available
        """
        try:
            # Import the marketplace scraper
            from src.services.discogs_marketplace_scraper import DiscogsMarketplaceScraper

            # Prepare scraper filters from VinylDigger filters
            scraper_filters = {}

            # Map VinylDigger filter names to scraper filter names
            if "min_record_condition" in filters:
                scraper_filters["condition"] = filters["min_record_condition"]

            if "seller_location_preference" in filters and filters["seller_location_preference"]:
                if filters["seller_location_preference"] != "ANY":
                    scraper_filters["seller_location_preference"] = filters["seller_location_preference"]

            if "genre" in filters and filters["genre"]:
                scraper_filters["genre"] = filters["genre"]

            if "style" in filters and filters["style"]:
                scraper_filters["style"] = filters["style"]

            # Map price filters
            if "min_price" in filters and filters["min_price"]:
                scraper_filters["price_min"] = filters["min_price"]
            if "max_price" in filters and filters["max_price"]:
                scraper_filters["price_max"] = filters["max_price"]

            # Map year filters
            if "year_from" in filters:
                scraper_filters["year_from"] = filters["year_from"]
            if "year_to" in filters:
                scraper_filters["year_to"] = filters["year_to"]

            # Set defaults
            scraper_filters["format"] = "Vinyl"
            page = filters.get("page", 1)
            limit = filters.get("limit", 50)

            # Use the marketplace scraper
            async with DiscogsMarketplaceScraper() as scraper:
                result = await scraper.search_marketplace(query, scraper_filters, page, limit)

                # Check for scraping errors
                if "error" in result:
                    self.logger.error(f"Marketplace scraping failed: {result.get('error')}")
                    # In production, we could implement fallback strategies here
                    # For now, return empty results
                    return []

                # Convert scraper results to VinylDigger format
                formatted_results = []
                for item in result.get("items", []):
                    formatted = self._format_scraped_marketplace_listing(item)
                    if formatted:
                        formatted_results.append(formatted)

                self.logger.info(f"Marketplace scraper found {len(formatted_results)} results for query: {query}")
                return formatted_results

        except Exception as e:
            self.logger.error(f"Discogs marketplace scraping error: {str(e)}")
            # Log additional context for debugging
            self.logger.error(f"Query: {query}, Filters: {filters}")
            return []

    async def get_item_details(self, item_id: str, db: AsyncSession, user_id: str) -> dict[str, Any] | None:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get OAuth auth
        auth = await self.get_oauth_auth(db, user_id)
        if not auth:
            return None

        try:
            # Get release details
            response = await self.client.get(f"/releases/{item_id}", auth=auth)
            response.raise_for_status()

            release_data = response.json()

            # Get marketplace listings for this release
            list_params = {
                "release_id": item_id,
                "status": "For Sale",
            }

            listings_response = await self.client.get("/marketplace/listings", params=list_params, auth=auth)
            listings_response.raise_for_status()

            listings_data = listings_response.json()

            return {
                "release": release_data,
                "listings": listings_data.get("listings", []),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error(f"Discogs authentication failed. User may need to reauthorize. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error getting item {item_id}: {str(e)}")
            return None
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error getting item {item_id}: {str(e)}")
            return None

    async def sync_collection(self, db: AsyncSession, user_id: str) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get OAuth auth
        auth = await self.get_oauth_auth(db, user_id)
        if not auth:
            return []

        try:
            # Get user's OAuth token to retrieve username (most recent if multiple exist)
            token_result = await db.execute(
                select(OAuthToken)
                .where(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == OAuthProvider.DISCOGS,
                )
                .order_by(OAuthToken.created_at.desc())
                .limit(1)
            )
            oauth_token = token_result.scalar_one_or_none()

            if not oauth_token or not oauth_token.provider_username:
                self.logger.error("Missing Discogs username for user")
                return []

            username = oauth_token.provider_username

            # Get collection
            collection = []
            page = 1

            while True:
                coll_params: dict[str, Any] = {"page": page, "per_page": 100}

                response = await self.client.get(
                    f"/users/{username}/collection/folders/0/releases", params=coll_params, auth=auth
                )
                response.raise_for_status()

                data = response.json()
                releases = data.get("releases", [])

                if not releases:
                    break

                for release in releases:
                    collection.append(
                        {
                            "id": release["id"],
                            "instance_id": release["instance_id"],
                            "basic_information": release["basic_information"],
                            "date_added": release["date_added"],
                            "rating": release.get("rating", 0),
                        }
                    )

                if page >= data["pagination"]["pages"]:
                    break

                page += 1
                await asyncio.sleep(0.5)  # Rate limiting

            return collection

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error(f"Discogs authentication failed. User may need to reauthorize. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error syncing collection: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error syncing collection: {str(e)}")
            return []

    async def sync_wantlist(self, db: AsyncSession, user_id: str) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get OAuth auth
        auth = await self.get_oauth_auth(db, user_id)
        if not auth:
            return []

        try:
            # Get user's OAuth token to retrieve username (most recent if multiple exist)
            token_result = await db.execute(
                select(OAuthToken)
                .where(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == OAuthProvider.DISCOGS,
                )
                .order_by(OAuthToken.created_at.desc())
                .limit(1)
            )
            oauth_token = token_result.scalar_one_or_none()

            if not oauth_token or not oauth_token.provider_username:
                self.logger.error("Missing Discogs username for user")
                return []

            username = oauth_token.provider_username

            # Get wantlist
            wantlist = []
            page = 1

            while True:
                want_params: dict[str, Any] = {"page": page, "per_page": 100}

                response = await self.client.get(f"/users/{username}/wants", params=want_params, auth=auth)
                response.raise_for_status()

                data = response.json()
                wants = data.get("wants", [])

                if not wants:
                    break

                for want in wants:
                    wantlist.append(
                        {
                            "id": want["id"],
                            "basic_information": want["basic_information"],
                            "date_added": want["date_added"],
                            "notes": want.get("notes", ""),
                            "rating": want.get("rating", 0),
                        }
                    )

                if page >= data["pagination"]["pages"]:
                    break

                page += 1
                await asyncio.sleep(0.5)  # Rate limiting

            return wantlist

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error(f"Discogs authentication failed. User may need to reauthorize. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error syncing wantlist: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error syncing wantlist: {str(e)}")
            return []

    def _format_scraped_marketplace_listing(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Format a scraped marketplace listing for VinylDigger compatibility."""
        try:
            # Extract seller information
            seller_info = item.get("seller", {})
            seller = {
                "id": seller_info.get("id"),
                "username": seller_info.get("username", "Unknown"),
                "rating": seller_info.get("rating"),
                "url": seller_info.get("url"),
            }

            # Extract price information
            price = item.get("price")
            currency = item.get("currency", "USD")
            shipping_cost = item.get("shipping_price")

            # Extract format information
            formats = item.get("format", [])
            if isinstance(formats, str):
                formats = [formats]

            return {
                "id": item.get("id"),  # Listing ID
                "release_id": item.get("release_id", item.get("id")),  # Release ID for cross-referencing
                "title": item.get("title", ""),
                "artist": item.get("artist", ""),
                "album": item.get("album", item.get("title", "")),  # For compatibility
                "year": item.get("year"),
                "country": item.get("country"),
                "format": formats,
                "label": item.get("label", []),
                "catno": item.get("catno"),
                "thumb": item.get("thumb", item.get("image_url")),
                "cover_image": item.get("cover_image", item.get("image_url")),
                "resource_url": item.get("resource_url", item.get("item_url")),
                "uri": item.get("uri", item.get("item_url")),
                # Actual marketplace data
                "price": price,
                "currency": currency,
                "condition": item.get("condition"),
                "sleeve_condition": item.get("sleeve_condition"),
                "seller": seller,
                "shipping_price": shipping_cost,
                "location": item.get("location"),
                "posted": item.get("posted"),
                "allow_offers": item.get("allow_offers", False),
                "status": item.get("status", "For Sale"),
                "ships_from": item.get("ships_from"),
                # For compatibility with existing code
                "master_id": item.get("master_id"),
                # Community data
                "community": item.get("community", {}),
            }
        except Exception as e:
            self.logger.error(f"Error formatting scraped Discogs marketplace listing: {str(e)}")
            return None

    def _format_marketplace_listing(self, listing: dict[str, Any]) -> dict[str, Any] | None:
        """Format a marketplace listing from Discogs API."""
        try:
            # Extract release information
            release = listing.get("release", {})
            basic_info = release.get("basic_information", {})

            # Extract title and artist
            title = basic_info.get("title", "")
            artists = basic_info.get("artists", [])
            artist_names = []
            for artist in artists:
                if isinstance(artist, dict):
                    artist_names.append(artist.get("name", ""))
                else:
                    artist_names.append(str(artist))
            artist = ", ".join(artist_names)

            # Extract seller information
            seller_info = listing.get("seller", {})
            seller = {
                "id": seller_info.get("id"),
                "username": seller_info.get("username", "Unknown"),
                "rating": seller_info.get("rating"),
                "stats": seller_info.get("stats", {}),
                "location": seller_info.get("location"),
                "shipping": seller_info.get("shipping"),
            }

            # Extract price information
            price_info = listing.get("price", {})
            price = None
            currency = "USD"
            if price_info:
                price = price_info.get("value")
                currency = price_info.get("currency", "USD")

            # Extract shipping information
            shipping_price = listing.get("shipping_price", {})
            shipping_cost = None
            if shipping_price:
                shipping_cost = shipping_price.get("value")

            # Extract format information
            formats = basic_info.get("formats", [])
            format_names = []
            for fmt in formats:
                if isinstance(fmt, dict):
                    format_names.append(fmt.get("name", ""))

            return {
                "id": listing.get("id"),  # Listing ID
                "release_id": release.get("id"),  # Release ID for cross-referencing
                "title": title,
                "artist": artist,
                "album": title,  # For compatibility
                "year": basic_info.get("year"),
                "country": basic_info.get("country"),
                "format": format_names,
                "label": [label.get("name", "") for label in basic_info.get("labels", [])],
                "catno": basic_info.get("labels", [{}])[0].get("catno") if basic_info.get("labels") else None,
                "thumb": basic_info.get("thumb"),
                "cover_image": basic_info.get("cover_image"),
                "resource_url": release.get("resource_url"),
                "uri": listing.get("uri"),
                # Actual marketplace data
                "price": price,
                "currency": currency,
                "condition": listing.get("condition"),
                "sleeve_condition": listing.get("sleeve_condition"),
                "seller": seller,
                "shipping_price": shipping_cost,
                "location": listing.get("location"),
                "posted": listing.get("posted"),
                "allow_offers": listing.get("allow_offers", False),
                "status": listing.get("status"),
                "ships_from": listing.get("ships_from"),
                # For compatibility with existing code
                "master_id": basic_info.get("master_id"),
            }
        except Exception as e:
            self.logger.error(f"Error formatting Discogs marketplace listing: {str(e)}")
            return None

    def _format_discogs_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Legacy method for formatting catalog items (kept for compatibility)."""
        try:
            # Extract basic info
            title = item.get("title", "")
            if " - " in title:
                artist, album = title.split(" - ", 1)
            else:
                artist = ""
                album = title

            return {
                "id": item.get("id"),
                "title": title,
                "artist": artist,
                "album": album,
                "year": item.get("year"),
                "country": item.get("country"),
                "format": item.get("format", []),
                "label": item.get("label", []),
                "catno": item.get("catno"),
                "barcode": item.get("barcode", []),
                "master_id": item.get("master_id"),
                "thumb": item.get("thumb"),
                "cover_image": item.get("cover_image"),
                "resource_url": item.get("resource_url"),
                "uri": item.get("uri"),
                # Note: No price/seller info in catalog data
                "price": None,
                "seller": None,
            }
        except Exception as e:
            self.logger.error(f"Error formatting Discogs item: {str(e)}")
            return None
