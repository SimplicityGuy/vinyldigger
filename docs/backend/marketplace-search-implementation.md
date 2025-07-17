# Marketplace Search Implementation

*Last updated: July 2025*

## Overview

VinylDigger has been updated to search actual marketplace listings instead of catalog databases. This fundamental change ensures users see real items for sale with actual prices and seller information.

## Architecture Changes

### Before: Catalog Database Search
```
User Search → Discogs /database/search → Release Information → No Prices/Sellers
```

### After: Marketplace Search
```
User Search → Discogs /marketplace/search → Live Listings → Real Prices/Sellers
```

## Implementation Details

### 1. Discogs Service Updates (`src/services/discogs.py`)

#### New Endpoint
- **Changed from**: `/database/search`
- **Changed to**: `/marketplace/search`

#### New Parameters
```python
params = {
    "q": query,
    "per_page": filters.get("limit", 50),
    "page": filters.get("page", 1),
    "format": "Vinyl",  # Focus on vinyl records
    "condition": filters.get("min_record_condition"),  # Media condition filter
    "seller_country": filters.get("seller_location_preference"),  # Location filter
    "price_min": str(filters.get("min_price", "")),  # Price range
    "price_max": str(filters.get("max_price", "")),
}
```

#### New Data Parser
- **Method**: `_format_marketplace_listing()`
- **Purpose**: Extract listing data with prices, sellers, conditions
- **Output**: Comprehensive listing information including marketplace-specific data

### 2. Data Structure Changes

#### Listing Data Structure
```python
{
    "id": listing.get("id"),  # Listing ID (unique)
    "release_id": release.get("id"),  # Release ID (for collection matching)
    "title": title,
    "artist": artist,
    "price": price,  # Actual asking price
    "currency": currency,
    "condition": listing.get("condition"),  # Media condition
    "sleeve_condition": listing.get("sleeve_condition"),  # Sleeve condition
    "seller": {  # Complete seller information
        "id": seller_info.get("id"),
        "username": seller_info.get("username"),
        "rating": seller_info.get("rating"),
        "location": seller_info.get("location"),
        "stats": seller_info.get("stats", {}),
    },
    "shipping_price": shipping_cost,
    # ... additional marketplace data
}
```

### 3. Seller Analysis Updates (`src/services/seller_analyzer.py`)

#### Enhanced Seller Extraction
```python
def _extract_discogs_seller(self, item_data: dict[str, Any]) -> dict[str, Any]:
    """Extract seller info from Discogs marketplace listing data."""
    seller_info = item_data.get("seller", {})

    return {
        "platform_seller_id": str(seller_info.get("id", "")),
        "seller_name": seller_info.get("username", "Unknown"),
        "location": seller_info.get("location", ""),
        "feedback_score": seller_info.get("rating", 0),
        "total_feedback_count": seller_info.get("stats", {}).get("total", 0),
        "positive_feedback_percentage": seller_info.get("rating", 0),
        "ships_internationally": True,
        "seller_metadata": seller_info,
    }
```

### 4. Item Processing Updates (`src/workers/tasks.py`)

#### Listing vs Release ID Handling
```python
# For marketplace listings, use listing ID as item_id to avoid duplicates
listing_id = str(item["id"])
release_id = str(item.get("release_id", item.get("id")))

# Check collection/wantlist using release_id (not listing_id)
is_in_collection = release_id in collection_releases
is_in_wantlist = release_id in wantlist_releases

# Create search result with listing_id for uniqueness
result = SearchResult(
    search_id=search.id,
    platform=SearchPlatform.DISCOGS,
    item_id=listing_id,  # Use listing ID for uniqueness
    item_data=item,
    is_in_collection=is_in_collection,
    is_in_wantlist=is_in_wantlist,
    # ... additional fields
)
```

## Benefits

### 1. Real Marketplace Data
- **Actual Prices**: Users see real asking prices, not "Price TBD"
- **Current Listings**: Only items currently for sale are shown
- **Live Inventory**: Reflects real-time marketplace availability

### 2. Enhanced Filtering
- **Condition Filters**: Filter by media and sleeve condition (M, NM, EX+, etc.)
- **Location Filters**: Filter by seller country/region
- **Price Range**: Set minimum and maximum price bounds

### 3. Improved Seller Analysis
- **Complete Profiles**: Full seller information with ratings and stats
- **Multi-item Detection**: Accurately identify sellers with multiple wanted items
- **Shipping Analysis**: Factor in actual shipping costs where available

### 4. Better Price Comparison
- **Cross-platform**: Compare real marketplace prices between Discogs and eBay
- **Historical Tracking**: Track actual price changes over time
- **Deal Identification**: Find genuine deals based on real market data

## Testing

### Search Parameters
```bash
# Example search with marketplace filters
{
    "query": "tiësto",
    "min_record_condition": "VG+",
    "seller_location_preference": "US",
    "min_price": 10,
    "max_price": 100
}
```

### Expected Results
- Real asking prices (e.g., $25.00 instead of "Price TBD")
- Seller usernames and ratings
- Media and sleeve conditions
- Shipping cost estimates
- Collection/wantlist match indicators

## Migration Notes

### Database Impact
- Existing search results may have different data structure
- Recommend dropping and recreating database for clean state
- New listings will have enhanced marketplace data

### API Compatibility
- Search API endpoints remain the same
- Response format enhanced with marketplace data
- Frontend automatically benefits from richer data

## Future Enhancements

### 1. Advanced Filtering
- Multiple condition criteria
- Seller rating thresholds
- Shipping cost optimization

### 2. Real-time Updates
- Live marketplace monitoring
- Price change notifications
- Inventory availability alerts

### 3. Enhanced Analytics
- Market trend analysis
- Price prediction modeling
- Seller reputation scoring
