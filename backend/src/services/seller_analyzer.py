"""Seller analysis service for multi-seller optimization and scoring."""

import re
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.search import SearchPlatform, SearchResult
from src.models.seller import Seller

logger = get_logger(__name__)


class SellerAnalysisService:
    """Service for analyzing sellers and finding optimal purchasing opportunities."""

    # Shipping cost estimates by region (USD)
    SHIPPING_ESTIMATES = {
        "US": {
            "US": 5.00,  # Domestic US shipping
            "CA": 15.00,  # US to Canada
            "EU": 25.00,  # US to Europe
            "UK": 25.00,  # US to UK
            "OTH": 35.00,  # US to rest of world
        },
        "CA": {
            "US": 15.00,  # Canada to US
            "CA": 8.00,  # Domestic Canada
            "EU": 20.00,  # Canada to Europe
            "UK": 20.00,  # Canada to UK
            "OTH": 30.00,  # Canada to rest of world
        },
        "EU": {
            "US": 25.00,  # Europe to US
            "CA": 20.00,  # Europe to Canada
            "EU": 12.00,  # Within Europe
            "UK": 15.00,  # Europe to UK
            "OTH": 30.00,  # Europe to rest of world
        },
        "UK": {
            "US": 25.00,  # UK to US
            "CA": 20.00,  # UK to Canada
            "EU": 15.00,  # UK to Europe
            "UK": 8.00,  # Domestic UK
            "OTH": 30.00,  # UK to rest of world
        },
        "OTH": {
            "US": 35.00,  # International to US
            "CA": 30.00,  # International to Canada
            "EU": 30.00,  # International to Europe
            "UK": 30.00,  # International to UK
            "OTH": 25.00,  # International to international
        },
    }

    @staticmethod
    def normalize_country_code(location: str | None) -> str:
        """Normalize location to country code for shipping estimates."""
        if not location:
            return "OTH"

        location_upper = location.upper()

        # Check for US state abbreviations first (to avoid CA confusion)
        # Only match if it ends with state abbreviation or has space after

        us_state_pattern = r"(, (AZ|CA|CO|FL|GA|IL|MA|MD|MI|MN|NC|NJ|NY|OH|OR|PA|TX|VA|WA|WI))(\s|$)"
        if re.search(us_state_pattern, location_upper):
            return "US"

        # US variations
        if any(term in location_upper for term in ["US", "USA", "UNITED STATES", "AMERICA"]):
            return "US"

        # Canada variations (check after US states to avoid CA state confusion)
        if any(term in location_upper for term in ["CANADA", "CANADIAN", "ONTARIO", "QUEBEC", "BRITISH COLUMBIA"]):
            return "CA"

        # UK variations
        if any(term in location_upper for term in ["UK", "GB", "BRITAIN", "ENGLAND", "SCOTLAND", "WALES"]):
            return "UK"

        # European countries
        eu_countries = [
            "GERMANY",
            "FRANCE",
            "ITALY",
            "SPAIN",
            "NETHERLANDS",
            "BELGIUM",
            "AUSTRIA",
            "SWEDEN",
            "DENMARK",
            "NORWAY",
            "FINLAND",
            "POLAND",
            "CZECH",
            "HUNGARY",
            "PORTUGAL",
            "IRELAND",
            "GREECE",
            "SWITZERLAND",
            "LUXEMBOURG",
        ]
        if any(country in location_upper for country in eu_countries):
            return "EU"

        return "OTH"

    async def extract_seller_info(self, item_data: dict[str, Any], platform: SearchPlatform) -> dict[str, Any]:
        """Extract seller information from item data."""
        if platform == SearchPlatform.DISCOGS:
            return self._extract_discogs_seller(item_data)
        elif platform == SearchPlatform.EBAY:
            return self._extract_ebay_seller(item_data)
        else:
            return {}

    def _extract_discogs_seller(self, item_data: dict[str, Any]) -> dict[str, Any]:
        """Extract seller info from Discogs marketplace listing data."""
        seller_info = item_data.get("seller", {})

        # Handle both old catalog format and new marketplace format
        if isinstance(seller_info, dict):
            # New marketplace format with detailed seller info
            return {
                "platform_seller_id": str(seller_info.get("id", "")),
                "seller_name": seller_info.get("username", "Unknown"),
                "location": seller_info.get("location", ""),
                "feedback_score": seller_info.get("rating", 0),
                "total_feedback_count": seller_info.get("stats", {}).get("total", 0),
                "positive_feedback_percentage": seller_info.get("rating", 0),
                "ships_internationally": True,  # Assume true for marketplace listings
                "seller_metadata": seller_info,
            }
        else:
            # Fallback for old format or missing seller info
            return {
                "platform_seller_id": "unknown",
                "seller_name": "Unknown Seller",
                "location": "",
                "feedback_score": 0,
                "total_feedback_count": 0,
                "positive_feedback_percentage": 0,
                "ships_internationally": True,
                "seller_metadata": {},
            }

    def _extract_ebay_seller(self, item_data: dict[str, Any]) -> dict[str, Any]:
        """Extract seller info from eBay item data."""
        seller_info = item_data.get("seller", {})

        # Extract feedback percentage (usually a string like "99.1%")
        feedback_pct = seller_info.get("feedbackPercentage", "0")
        if isinstance(feedback_pct, str):
            feedback_pct = feedback_pct.replace("%", "")
            try:
                feedback_pct = float(feedback_pct)
            except ValueError:
                feedback_pct = 0.0

        return {
            "platform_seller_id": seller_info.get("username", ""),
            "seller_name": seller_info.get("username", "Unknown"),
            "location": item_data.get("itemLocation", {}).get("country", ""),
            "feedback_score": feedback_pct,
            "total_feedback_count": seller_info.get("feedbackScore", 0),
            "positive_feedback_percentage": feedback_pct,
            "ships_internationally": True,  # Most eBay sellers ship internationally
            "seller_metadata": seller_info,
        }

    async def find_or_create_seller(
        self, db: AsyncSession, platform: SearchPlatform, seller_info: dict[str, Any]
    ) -> Seller:
        """Find existing seller or create new one."""
        platform_seller_id = seller_info.get("platform_seller_id", "")

        if not platform_seller_id:
            # Create anonymous seller for missing seller info
            platform_seller_id = f"anonymous_{hash(seller_info.get('seller_name', 'unknown'))}"

        # Try to find existing seller
        result = await db.execute(
            select(Seller).where(Seller.platform == platform, Seller.platform_seller_id == platform_seller_id)
        )
        existing_seller = result.scalar_one_or_none()

        if existing_seller:
            # Update seller info with latest data
            existing_seller.seller_name = seller_info.get("seller_name", existing_seller.seller_name)
            existing_seller.location = seller_info.get("location", existing_seller.location)
            existing_seller.feedback_score = seller_info.get("feedback_score", existing_seller.feedback_score)
            existing_seller.total_feedback_count = seller_info.get(
                "total_feedback_count", existing_seller.total_feedback_count
            )
            existing_seller.positive_feedback_percentage = seller_info.get(
                "positive_feedback_percentage", existing_seller.positive_feedback_percentage
            )
            existing_seller.ships_internationally = seller_info.get(
                "ships_internationally", existing_seller.ships_internationally
            )
            existing_seller.seller_metadata = seller_info.get("seller_metadata", existing_seller.seller_metadata)

            # Update country code for shipping estimates
            existing_seller.country_code = self.normalize_country_code(existing_seller.location)

            return existing_seller

        # Create new seller
        new_seller = Seller(
            platform=platform,
            platform_seller_id=platform_seller_id,
            seller_name=seller_info.get("seller_name", "Unknown"),
            location=seller_info.get("location", ""),
            country_code=self.normalize_country_code(seller_info.get("location")),
            feedback_score=seller_info.get("feedback_score"),
            total_feedback_count=seller_info.get("total_feedback_count"),
            positive_feedback_percentage=seller_info.get("positive_feedback_percentage"),
            ships_internationally=seller_info.get("ships_internationally", False),
            seller_metadata=seller_info.get("seller_metadata"),
        )

        db.add(new_seller)
        # Let SQLAlchemy handle flushing automatically
        return new_seller

    async def analyze_seller_inventory(self, db: AsyncSession, seller: Seller, user_id: str) -> dict[str, Any]:
        """Analyze a seller's inventory for want list matches and value."""

        # Get all search results from this seller
        result = await db.execute(select(SearchResult).where(SearchResult.seller_id == seller.id))
        search_results = result.scalars().all()

        if not search_results:
            return {
                "total_items": 0,
                "wantlist_items": 0,
                "collection_duplicates": 0,
                "total_value": Decimal("0.00"),
                "avg_item_price": Decimal("0.00"),
                "estimated_shipping": Decimal("0.00"),
            }

        # Count items and calculate values
        total_items = len(search_results)
        wantlist_items = sum(1 for r in search_results if r.is_in_wantlist)
        collection_duplicates = sum(1 for r in search_results if r.is_in_collection)

        # Calculate total value
        total_value = Decimal("0.00")
        valid_prices = []

        for search_result in search_results:
            if search_result.item_price:
                total_value += search_result.item_price
                valid_prices.append(search_result.item_price)

        avg_item_price = total_value / len(valid_prices) if valid_prices else Decimal("0.00")

        # Estimate shipping based on seller location
        estimated_shipping = self.estimate_shipping_cost(seller, user_id, total_items)

        return {
            "total_items": total_items,
            "wantlist_items": wantlist_items,
            "collection_duplicates": collection_duplicates,
            "total_value": total_value,
            "avg_item_price": avg_item_price,
            "estimated_shipping": estimated_shipping,
        }

    def estimate_shipping_cost(
        self,
        seller: Seller,
        user_id: str,
        item_count: int = 1,
        user_location: str = "US",  # TODO: Get from user preferences
    ) -> Decimal:
        """Estimate shipping cost based on seller and user locations."""

        seller_country = seller.country_code or "OTH"
        user_country = self.normalize_country_code(user_location)

        # Get base shipping cost
        base_cost = self.SHIPPING_ESTIMATES.get(seller_country, {}).get(user_country, 35.00)

        # Adjust for multiple items (diminishing returns)
        if item_count > 1:
            # Each additional item adds 20% of base cost
            additional_cost = base_cost * 0.2 * (item_count - 1)
            total_cost = base_cost + additional_cost
        else:
            total_cost = base_cost

        # Use seller's estimated shipping if available and reasonable
        if seller.estimated_shipping_cost:
            seller_estimate = float(seller.estimated_shipping_cost)
            # Use seller estimate if it's within 50% of our estimate
            if 0.5 * total_cost <= seller_estimate <= 1.5 * total_cost:
                total_cost = seller_estimate

        return Decimal(str(total_cost))

    async def score_seller_reputation(self, seller: Seller) -> Decimal:
        """Score seller reputation (0-100)."""
        score = Decimal("50.0")  # Start with neutral score

        # Feedback score component (0-40 points)
        if seller.feedback_score is not None:
            feedback_score = float(seller.feedback_score)
            if seller.platform == SearchPlatform.DISCOGS:
                # Discogs uses 0-100 rating
                score += Decimal(str(feedback_score * 0.4))
            elif seller.platform == SearchPlatform.EBAY:
                # eBay uses percentage
                score += Decimal(str(feedback_score * 0.4))

        # Feedback count component (0-30 points)
        if seller.total_feedback_count:
            count = seller.total_feedback_count
            # Logarithmic scaling: more feedback is better but with diminishing returns
            if count >= 1000:
                score += Decimal("30.0")
            elif count >= 500:
                score += Decimal("25.0")
            elif count >= 100:
                score += Decimal("20.0")
            elif count >= 50:
                score += Decimal("15.0")
            elif count >= 10:
                score += Decimal("10.0")
            else:
                score += Decimal("5.0")

        # Positive feedback percentage (0-30 points)
        if seller.positive_feedback_percentage is not None:
            pct = float(seller.positive_feedback_percentage)
            if pct >= 99.0:
                score += Decimal("30.0")
            elif pct >= 98.0:
                score += Decimal("25.0")
            elif pct >= 95.0:
                score += Decimal("20.0")
            elif pct >= 90.0:
                score += Decimal("15.0")
            else:
                score += Decimal("10.0")

        return min(score, Decimal("100.0"))

    async def calculate_location_preference_score(
        self, seller: Seller, preferred_location: str | None = None
    ) -> Decimal:
        """Calculate location preference score (0-100)."""
        if not preferred_location:
            return Decimal("50.0")  # Neutral if no preference

        seller_country = seller.country_code or "OTH"
        preferred_country = self.normalize_country_code(preferred_location)

        if seller_country == preferred_country:
            return Decimal("100.0")  # Perfect match
        elif seller_country == "OTH" or preferred_country == "OTH":
            return Decimal("30.0")  # Unknown location penalty
        else:
            return Decimal("10.0")  # Different location penalty

    async def find_multi_item_opportunities(
        self, db: AsyncSession, search_id: str, min_items: int = 2
    ) -> list[dict[str, Any]]:
        """Find sellers with multiple items in a search."""
        from uuid import UUID

        # Convert string search_id to UUID for database query
        search_uuid = UUID(search_id) if isinstance(search_id, str) else search_id

        # Query for sellers with multiple items
        query = (
            select(
                SearchResult.seller_id,
                func.count(SearchResult.id).label("item_count"),
                func.sum(SearchResult.item_price).label("total_value"),
                func.sum(case((SearchResult.is_in_wantlist.is_(True), 1), else_=0)).label("wantlist_count"),
            )
            .where(SearchResult.search_id == search_uuid, SearchResult.seller_id.is_not(None))
            .group_by(SearchResult.seller_id)
            .having(func.count(SearchResult.id) >= min_items)
            .order_by(func.count(SearchResult.id).desc())
        )

        result = await db.execute(query)
        multi_item_sellers = result.all()

        opportunities = []
        for row in multi_item_sellers:
            seller_result = await db.execute(select(Seller).where(Seller.id == row.seller_id))
            seller = seller_result.scalar_one_or_none()

            if seller:
                opportunities.append(
                    {
                        "seller": seller,
                        "item_count": row.item_count,
                        "total_value": row.total_value or Decimal("0.00"),
                        "wantlist_count": row.wantlist_count or 0,
                        "potential_shipping_savings": self.calculate_shipping_savings(row.item_count, seller),
                    }
                )

        return opportunities

    def calculate_shipping_savings(self, item_count: int, seller: Seller) -> Decimal:
        """Calculate potential shipping savings from buying multiple items."""
        if item_count <= 1:
            return Decimal("0.00")

        # Calculate individual shipping costs vs combined
        single_item_shipping = self.estimate_shipping_cost(seller, "dummy_user", 1)
        combined_shipping = self.estimate_shipping_cost(seller, "dummy_user", item_count)

        individual_total = single_item_shipping * item_count
        savings = individual_total - combined_shipping

        return max(savings, Decimal("0.00"))
