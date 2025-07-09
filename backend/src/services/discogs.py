import asyncio
from typing import Any

import httpx
from httpx import AsyncClient

from src.models.api_key import APIService
from src.services.base import BaseAPIService


class DiscogsService(BaseAPIService):
    BASE_URL = "https://api.discogs.com"

    def __init__(self):
        super().__init__(APIService.DISCOGS)
        self.client: AsyncClient | None = None

    async def __aenter__(self):
        self.client = AsyncClient(
            base_url=self.BASE_URL,
            headers={"User-Agent": "VinylDigger/1.0"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def search(self, query: str, filters: dict[str, Any], credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        params = {
            "q": query,
            "token": credentials["key"],
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
            response = await self.client.get("/database/search", params=params)
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

        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error: {str(e)}")
            return []

    async def get_item_details(self, item_id: str, credentials: dict[str, str]) -> dict[str, Any] | None:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        try:
            # Get release details
            response = await self.client.get(f"/releases/{item_id}", params={"token": credentials["key"]})
            response.raise_for_status()

            release_data = response.json()

            # Get marketplace listings for this release
            listings_response = await self.client.get(
                "/marketplace/listings",
                params={
                    "release_id": item_id,
                    "token": credentials["key"],
                    "status": "For Sale",
                },
            )
            listings_response.raise_for_status()

            listings_data = listings_response.json()

            return {
                "release": release_data,
                "listings": listings_data.get("listings", []),
            }

        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error getting item {item_id}: {str(e)}")
            return None

    async def sync_collection(self, credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        try:
            # Get user info first
            user_response = await self.client.get("/oauth/identity", params={"token": credentials["key"]})
            user_response.raise_for_status()
            user_data = user_response.json()
            username = user_data["username"]

            # Get collection
            collection = []
            page = 1

            while True:
                response = await self.client.get(
                    f"/users/{username}/collection/folders/0/releases",
                    params={"token": credentials["key"], "page": page, "per_page": 100},
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

        except httpx.HTTPError as e:
            self.logger.error(f"Discogs API error syncing collection: {str(e)}")
            return []

    async def sync_wantlist(self, credentials: dict[str, str]) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        try:
            # Get user info first
            user_response = await self.client.get("/oauth/identity", params={"token": credentials["key"]})
            user_response.raise_for_status()
            user_data = user_response.json()
            username = user_data["username"]

            # Get wantlist
            wantlist = []
            page = 1

            while True:
                response = await self.client.get(
                    f"/users/{username}/wants",
                    params={"token": credentials["key"], "page": page, "per_page": 100},
                )
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
