import base64
from typing import Any
from uuid import UUID

import httpx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models import AppConfig, OAuthProvider, OAuthToken


class EbayService:
    SANDBOX_URL = "https://api.sandbox.ebay.com"
    PRODUCTION_URL = "https://api.ebay.com"

    def __init__(self, use_sandbox: bool = False) -> None:
        self.logger = get_logger(__name__)
        self.base_url = self.SANDBOX_URL if use_sandbox else self.PRODUCTION_URL
        self.client: AsyncClient | None = None
        self.access_token: str | None = None

    async def __aenter__(self) -> "EbayService":
        self.client = AsyncClient(
            base_url=self.base_url,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.client:
            await self.client.aclose()

    async def get_oauth_token(self, db: AsyncSession, user_id: UUID) -> str | None:
        """Get user's OAuth access token for eBay."""
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == OAuthProvider.EBAY,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return None

        # TODO: Check if token is expired and refresh if needed
        return token.access_token

    async def _get_app_access_token(self, db: AsyncSession) -> str | None:
        """Get application access token using client credentials flow."""
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get app configuration
        result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.EBAY))
        app_config = result.scalar_one_or_none()

        if not app_config:
            self.logger.error("eBay OAuth is not configured")
            return None

        try:
            # Create Basic auth header
            auth_string = f"{app_config.consumer_key}:{app_config.consumer_secret}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            response = await self.client.post(
                "/identity/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": app_config.scope or "https://api.ebay.com/oauth/api_scope",
                },
            )
            response.raise_for_status()

            data = response.json()
            access_token = data.get("access_token")
            return str(access_token) if access_token else None

        except httpx.HTTPError as e:
            self.logger.error(f"eBay auth error: {str(e)}")
            return None

    async def search(
        self, query: str, filters: dict[str, Any], db: AsyncSession, user_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get access token if not cached
        if not self.access_token:
            # Try user OAuth token first if user_id provided
            if user_id:
                self.access_token = await self.get_oauth_token(db, user_id)

            # Fall back to app token if no user token
            if not self.access_token:
                self.access_token = await self._get_app_access_token(db)

            if not self.access_token:
                self.logger.error("Failed to get eBay access token")
                return []

        # Build filter string
        filter_parts = []

        # Category filter for vinyl records
        if filters.get("category_id"):
            filter_parts.append(f"categoryIds:{{{filters['category_id']}}}")
        else:
            # Default to vinyl records category
            filter_parts.append("categoryIds:{176985}")

        # Condition filter
        if "condition" in filters:
            conditions = filters["condition"] if isinstance(filters["condition"], list) else [filters["condition"]]
            condition_values = {
                "new": "NEW",
                "like_new": "LIKE_NEW",
                "very_good": "VERY_GOOD",
                "good": "GOOD",
                "acceptable": "ACCEPTABLE",
            }
            ebay_conditions = [condition_values.get(c, c.upper()) for c in conditions]
            filter_parts.append(f"conditions:{{{','.join(ebay_conditions)}}}")

        # Price range
        if "min_price" in filters:
            filter_parts.append(f"price:[{filters['min_price']}..{filters.get('max_price', '*')}]")
        elif "max_price" in filters:
            filter_parts.append(f"price:[0..{filters['max_price']}]")

        # Location filter
        if "item_location" in filters:
            filter_parts.append(f"itemLocationCountry:{filters['item_location']}")

        filter_string = ",".join(filter_parts) if filter_parts else None

        params = {
            "q": query,
            "limit": min(filters.get("limit", 50), 200),  # eBay max is 200
            "offset": filters.get("offset", 0),
        }

        if filter_string:
            params["filter"] = filter_string

        # Sort options
        sort_map = {
            "price_asc": "price",
            "price_desc": "-price",
            "date_desc": "-date",
            "distance": "distance",
        }
        if "sort" in filters:
            params["sort"] = sort_map.get(filters["sort"], "best_match")

        try:
            response = await self.client.get(
                "/buy/browse/v1/item_summary/search",
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("itemSummaries", []):
                formatted = self._format_ebay_item(item)
                if formatted:
                    results.append(formatted)

            return results

        except httpx.HTTPError as e:
            self.logger.error(f"eBay API search error: {str(e)}")
            # If auth error, clear token to retry next time
            if hasattr(e, "response") and e.response and e.response.status_code == 401:
                self.access_token = None
            return []

    async def get_item_details(
        self, item_id: str, db: AsyncSession, user_id: UUID | None = None
    ) -> dict[str, Any] | None:
        if not self.client:
            raise RuntimeError("Service not initialized. Use async with context.")

        # Get access token if not cached
        if not self.access_token:
            # Try user OAuth token first if user_id provided
            if user_id:
                self.access_token = await self.get_oauth_token(db, user_id)

            # Fall back to app token if no user token
            if not self.access_token:
                self.access_token = await self._get_app_access_token(db)

            if not self.access_token:
                self.logger.error("Failed to get eBay access token")
                return None

        try:
            response = await self.client.get(
                f"/buy/browse/v1/item/{item_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()

            result: dict[str, Any] = response.json()
            return result

        except httpx.HTTPError as e:
            self.logger.error(f"eBay API error getting item {item_id}: {str(e)}")
            # If auth error, clear token to retry next time
            if hasattr(e, "response") and e.response and e.response.status_code == 401:
                self.access_token = None
            return None

    def _format_ebay_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        try:
            # Extract price info
            price_info = item.get("price", {})
            price = float(price_info.get("value", 0))
            currency = price_info.get("currency", "USD")

            # Extract shipping info
            shipping_options = item.get("shippingOptions", [])
            shipping_cost = 0.0
            if shipping_options:
                shipping_cost = float(shipping_options[0].get("shippingCost", {}).get("value", 0))

            # Extract seller info
            seller = item.get("seller", {})

            return {
                "id": item.get("itemId"),
                "title": item.get("title"),
                "subtitle": item.get("subtitle"),
                "condition": item.get("condition"),
                "condition_id": item.get("conditionId"),
                "price": price,
                "currency": currency,
                "shipping_cost": shipping_cost,
                "total_price": price + shipping_cost,
                "buy_it_now": item.get("buyingOptions", []) and "FIXED_PRICE" in item["buyingOptions"],
                "auction": item.get("buyingOptions", []) and "AUCTION" in item["buyingOptions"],
                "best_offer": item.get("buyingOptions", []) and "BEST_OFFER" in item["buyingOptions"],
                "current_bid_price": item.get("currentBidPrice", {}).get("value"),
                "seller": {
                    "username": seller.get("username"),
                    "feedback_percentage": seller.get("feedbackPercentage"),
                    "feedback_score": seller.get("feedbackScore"),
                },
                "location": {
                    "city": item.get("itemLocation", {}).get("city"),
                    "state": item.get("itemLocation", {}).get("stateOrProvince"),
                    "country": item.get("itemLocation", {}).get("country"),
                    "postal_code": item.get("itemLocation", {}).get("postalCode"),
                },
                "image_url": item.get("image", {}).get("imageUrl"),
                "additional_images": [img.get("imageUrl") for img in item.get("additionalImages", [])],
                "item_web_url": item.get("itemWebUrl"),
                "categories": [cat.get("categoryName") for cat in item.get("categories", [])],
                "item_end_date": item.get("itemEndDate"),
            }
        except Exception as e:
            self.logger.error(f"Error formatting eBay item: {str(e)}")
            return None
