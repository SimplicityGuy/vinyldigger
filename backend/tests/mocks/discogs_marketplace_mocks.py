"""
Mock data generator for Discogs marketplace testing.

This module provides mock marketplace data for testing purposes only.
It should NOT be used in production code.
"""

from typing import Any


class DiscogsMarketplaceMockGenerator:
    """Generate mock marketplace data for testing."""

    @staticmethod
    def generate_mock_listing(
        listing_id: str,
        release_id: str,
        artist: str = "Mock Artist",
        album: str = "Mock Album",
        price: float = 19.99,
        condition: str = "Near Mint (NM or M-)",
        seller_username: str = "MockSeller",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a single mock marketplace listing."""
        return {
            "id": listing_id,
            "release_id": release_id,
            "title": f"{artist} - {album}",
            "artist": artist,
            "album": album,
            "year": kwargs.get("year", 1970),
            "country": kwargs.get("country", "US"),
            "format": kwargs.get("format", ["Vinyl", "LP", "Album"]),
            "label": kwargs.get("label", ["Mock Records"]),
            "catno": kwargs.get("catno", "MR-001"),
            "condition": condition,
            "sleeve_condition": kwargs.get("sleeve_condition", condition),
            "price": price,
            "currency": kwargs.get("currency", "USD"),
            "shipping_price": kwargs.get("shipping_price", 4.99),
            "seller": {
                "id": kwargs.get("seller_id", "seller123"),
                "username": seller_username,
                "rating": kwargs.get("seller_rating", 98.5),
                "url": f"https://www.discogs.com/seller/{seller_username}",
            },
            "community": {"have": kwargs.get("have_count", 100), "want": kwargs.get("want_count", 50)},
            "image_url": kwargs.get("image_url", f"https://i.discogs.com/mock-{listing_id}.jpg"),
            "item_url": f"https://www.discogs.com/sell/item/{listing_id}",
            "thumb": kwargs.get("thumb", f"https://i.discogs.com/mock-thumb-{listing_id}.jpg"),
            "cover_image": kwargs.get("cover_image", f"https://i.discogs.com/mock-cover-{listing_id}.jpg"),
            "resource_url": f"https://api.discogs.com/releases/{release_id}",
            "uri": f"/releases/{release_id}",
            "location": kwargs.get("location", "United States"),
            "posted": kwargs.get("posted", "2024-01-01T00:00:00-00:00"),
            "allow_offers": kwargs.get("allow_offers", False),
            "status": kwargs.get("status", "For Sale"),
            "ships_from": kwargs.get("ships_from", "US"),
        }

    @staticmethod
    def generate_mock_search_results(
        query: str, page: int = 1, limit: int = 10, total: int = 100, **kwargs: Any
    ) -> dict[str, Any]:
        """Generate mock search results for testing."""
        items = []
        base_id = 1000000 + (page - 1) * limit

        # Parse query to extract artist/album info
        if " - " in query:
            artist, album = query.split(" - ", 1)
        elif len(query.split()) > 1:
            parts = query.split()
            artist = parts[0]
            album = " ".join(parts[1:])
        else:
            artist = query
            album = f"{query} Album"

        for i in range(min(limit, total - (page - 1) * limit)):
            listing_id = str(base_id + 500000 + i)
            release_id = str(base_id + i)

            mock_item = DiscogsMarketplaceMockGenerator.generate_mock_listing(
                listing_id=listing_id,
                release_id=release_id,
                artist=artist,
                album=f"{album} (Edition {i + 1})",
                price=15.99 + (i * 5.0),
                condition=["Mint (M)", "Near Mint (NM or M-)", "Very Good Plus (VG+)"][i % 3],
                seller_username=f"MockSeller{i + 1}",
                year=1970 + (i * 5),
                seller_rating=95.0 + i,
                have_count=50 + (i * 10),
                want_count=25 + (i * 5),
                shipping_price=4.99 if i % 2 == 0 else None,
                allow_offers=i % 2 == 0,
            )
            items.append(mock_item)

        return {
            "items": items,
            "total": total,
            "page": {"current": page, "limit": limit, "total_pages": (total + limit - 1) // limit},
            "url_generated": f"https://www.discogs.com/sell/list?q={query}&page={page}&limit={limit}",
        }

    @staticmethod
    def generate_empty_results() -> dict[str, Any]:
        """Generate empty search results for testing."""
        return {
            "items": [],
            "total": 0,
            "page": {"current": 1, "limit": 50, "total_pages": 0},
            "url_generated": "https://www.discogs.com/sell/list",
        }
