import asyncio
from typing import Any

import httpx
from httpx import AsyncClient

from src.models.api_key import APIService
from src.services.base import BaseAPIService


class DiscogsService(BaseAPIService):
    BASE_URL = "https://api.discogs.com"

    def __init__(self) -> None:
        super().__init__(APIService.DISCOGS)
        self.client: AsyncClient | None = None

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

    async def search(self, query: str, filters: dict[str, Any], credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Prepare authentication headers
        headers = self._get_auth_headers(credentials)

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
            # Add token to params only if not using Authorization header
            if not headers:
                params["token"] = credentials["key"]

            response = await self.client.get("/database/search", params=params, headers=headers)
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
                self.logger.error(f"Discogs authentication failed. Please check your API token. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error: {str(e)}")
            return []

    async def get_item_details(self, item_id: str, credentials: dict[str, str]) -> dict[str, Any] | None:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Prepare authentication headers
        headers = self._get_auth_headers(credentials)
        params = {}
        if not headers:
            params["token"] = credentials["key"]

        try:
            # Get release details
            response = await self.client.get(f"/releases/{item_id}", params=params, headers=headers)
            response.raise_for_status()

            release_data = response.json()

            # Get marketplace listings for this release
            list_params = {
                "release_id": item_id,
                "status": "For Sale",
            }
            if not headers:
                list_params["token"] = credentials["key"]

            listings_response = await self.client.get("/marketplace/listings", params=list_params, headers=headers)
            listings_response.raise_for_status()

            listings_data = listings_response.json()

            return {
                "release": release_data,
                "listings": listings_data.get("listings", []),
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.logger.error(f"Discogs authentication failed. Please check your API token. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error getting item {item_id}: {str(e)}")
            return None
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error getting item {item_id}: {str(e)}")
            return None

    async def sync_collection(self, credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Prepare authentication headers
        headers = self._get_auth_headers(credentials)

        try:
            # Get user info first
            identity_params = {}
            if not headers:
                identity_params["token"] = credentials["key"]

            user_response = await self.client.get("/oauth/identity", params=identity_params, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
            username = user_data["username"]

            # Get collection
            collection = []
            page = 1

            while True:
                coll_params: dict[str, Any] = {"page": page, "per_page": 100}
                if not headers:
                    coll_params["token"] = credentials["key"]

                response = await self.client.get(
                    f"/users/{username}/collection/folders/0/releases", params=coll_params, headers=headers
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
                self.logger.error(f"Discogs authentication failed. Please check your API token. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error syncing collection: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error syncing collection: {str(e)}")
            return []

    async def sync_wantlist(self, credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Prepare authentication headers
        headers = self._get_auth_headers(credentials)

        try:
            # Get user info first
            identity_params = {}
            if not headers:
                identity_params["token"] = credentials["key"]

            user_response = await self.client.get("/oauth/identity", params=identity_params, headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
            username = user_data["username"]

            # Get wantlist
            wantlist = []
            page = 1

            while True:
                want_params: dict[str, Any] = {"page": page, "per_page": 100}
                if not headers:
                    want_params["token"] = credentials["key"]

                response = await self.client.get(f"/users/{username}/wants", params=want_params, headers=headers)
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
                self.logger.error(f"Discogs authentication failed. Please check your API token. Error: {str(e)}")
            else:
                self.logger.error(f"Discogs API error syncing wantlist: {str(e)}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error syncing wantlist: {str(e)}")
            return []

    def _get_auth_headers(self, credentials: dict[str, str]) -> dict[str, str]:
        """Get authentication headers for Discogs API.

        Supports both Personal Access Tokens and OAuth tokens.
        """
        token = credentials.get("key", "")

        # Check if it's a personal access token (usually longer and contains specific patterns)
        if len(token) > 32 or "-" in token:
            # Personal Access Token - use Authorization header
            return {"Authorization": f"Discogs token={token}"}
        else:
            # OAuth token - use token parameter (will be added to URL params)
            return {}

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
