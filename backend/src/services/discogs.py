import asyncio
from typing import Any
from uuid import UUID

import httpx
from httpx import AsyncClient
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

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """Apply OAuth1 signature to the request."""
        # Convert httpx request to a format oauthlib can work with
        uri = str(request.url)
        method = request.method
        body = request.content.decode() if request.content else None
        headers = dict(request.headers)

        # Generate OAuth signature
        uri, headers, body = self.oauth_client.sign(uri, http_method=method, body=body, headers=headers)

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

        # Get user's OAuth token
        token_result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == UUID(user_id),
                OAuthToken.provider == OAuthProvider.DISCOGS,
            )
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
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get OAuth auth
        auth = await self.get_oauth_auth(db, user_id)
        if not auth:
            return []

        params = {
            "q": query,
            "per_page": filters.get("limit", 50),
            "page": filters.get("page", 1),
        }

        # Add format filter if specified
        if "format" in filters:
            params["format"] = filters["format"]

        # Add genre/style filters
        if "genre" in filters:
            params["genre"] = filters["genre"]
        if "style" in filters:
            params["style"] = filters["style"]

        # Add year range
        if "year_from" in filters:
            params["year"] = f"{filters['year_from']}-{filters.get('year_to', '')}"
        elif "year_to" in filters:
            params["year"] = f"-{filters['year_to']}"

        try:
            response = await self.client.get("/database/search", params=params, auth=auth)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("results", []):
                # Only process marketplace listings
                if item.get("type") in ["release", "master"]:
                    formatted = self._format_discogs_item(item)
                    if formatted:
                        results.append(formatted)

            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error(f"Discogs authentication failed. User may need to reauthorize. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error: {str(e)}")
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
            # Get user's OAuth token to retrieve username
            token_result = await db.execute(
                select(OAuthToken).where(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == OAuthProvider.DISCOGS,
                )
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
            # Get user's OAuth token to retrieve username
            token_result = await db.execute(
                select(OAuthToken).where(
                    OAuthToken.user_id == UUID(user_id),
                    OAuthToken.provider == OAuthProvider.DISCOGS,
                )
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

    def _format_discogs_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
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
            }
        except Exception as e:
            self.logger.error(f"Error formatting Discogs item: {str(e)}")
            return None
