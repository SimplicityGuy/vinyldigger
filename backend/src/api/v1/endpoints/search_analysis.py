"""Search analysis API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.search import SavedSearch
from src.models.search_analysis import DealRecommendation, SearchResultAnalysis, SellerAnalysis
from src.models.seller import Seller
from src.models.user import User

router = APIRouter()


@router.get("/search/{search_id}/analysis")
async def get_search_analysis(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive analysis for a search."""

    # Verify search belongs to user
    search_result = await db.execute(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == current_user.id)
    )
    search = search_result.scalar_one_or_none()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Get analysis data
    analysis_result = await db.execute(select(SearchResultAnalysis).where(SearchResultAnalysis.search_id == search_id))
    analysis = analysis_result.scalar_one_or_none()

    if not analysis:
        return {
            "search_id": str(search_id),
            "analysis_completed": False,
            "message": "Analysis not yet completed for this search",
        }

    # Get recommendations
    recommendations_result = await db.execute(
        select(DealRecommendation)
        .where(DealRecommendation.analysis_id == analysis.id)
        .order_by(DealRecommendation.score_value.desc())
    )
    recommendations = recommendations_result.scalars().all()

    # Get seller analyses
    seller_analyses_result = await db.execute(
        select(SellerAnalysis)
        .where(SellerAnalysis.search_analysis_id == analysis.id)
        .order_by(SellerAnalysis.recommendation_rank)
    )
    seller_analyses = seller_analyses_result.scalars().all()

    # Format recommendations
    formatted_recommendations = []
    for rec in recommendations:
        seller_result = await db.execute(select(Seller).where(Seller.id == rec.seller_id))
        seller = seller_result.scalar_one_or_none()

        formatted_recommendations.append(
            {
                "id": str(rec.id),
                "type": rec.recommendation_type.value,
                "deal_score": rec.deal_score.value,
                "score_value": float(rec.score_value),
                "title": rec.title,
                "description": rec.description,
                "recommendation_reason": rec.recommendation_reason,
                "total_items": rec.total_items,
                "wantlist_items": rec.wantlist_items,
                "total_value": float(rec.total_value),
                "estimated_shipping": float(rec.estimated_shipping) if rec.estimated_shipping else None,
                "total_cost": float(rec.total_cost),
                "potential_savings": float(rec.potential_savings) if rec.potential_savings else None,
                "seller": {
                    "id": str(seller.id) if seller else None,
                    "name": seller.seller_name if seller else "Unknown",
                    "location": seller.location if seller else None,
                    "feedback_score": float(seller.feedback_score) if seller and seller.feedback_score else None,
                }
                if seller
                else None,
                "item_ids": rec.item_ids,
            }
        )

    # Format seller analyses
    formatted_seller_analyses = []
    for seller_analysis in seller_analyses:
        seller_result = await db.execute(select(Seller).where(Seller.id == seller_analysis.seller_id))
        seller = seller_result.scalar_one_or_none()

        formatted_seller_analyses.append(
            {
                "rank": seller_analysis.recommendation_rank,
                "total_items": seller_analysis.total_items,
                "wantlist_items": seller_analysis.wantlist_items,
                "total_value": float(seller_analysis.total_value),
                "estimated_shipping": float(seller_analysis.estimated_shipping)
                if seller_analysis.estimated_shipping
                else None,
                "overall_score": float(seller_analysis.overall_score),
                "price_competitiveness": float(seller_analysis.price_competitiveness),
                "inventory_depth_score": float(seller_analysis.inventory_depth_score),
                "seller_reputation_score": float(seller_analysis.seller_reputation_score),
                "location_preference_score": float(seller_analysis.location_preference_score),
                "seller": {
                    "id": str(seller.id) if seller else None,
                    "name": seller.seller_name if seller else "Unknown",
                    "location": seller.location if seller else None,
                    "country_code": seller.country_code if seller else None,
                    "feedback_score": float(seller.feedback_score) if seller and seller.feedback_score else None,
                    "total_feedback_count": seller.total_feedback_count if seller else None,
                }
                if seller
                else None,
            }
        )

    return {
        "search_id": str(search_id),
        "analysis_completed": True,
        "analysis": {
            "id": str(analysis.id),
            "total_results": analysis.total_results,
            "total_sellers": analysis.total_sellers,
            "multi_item_sellers": analysis.multi_item_sellers,
            "min_price": float(analysis.min_price) if analysis.min_price else None,
            "max_price": float(analysis.max_price) if analysis.max_price else None,
            "avg_price": float(analysis.avg_price) if analysis.avg_price else None,
            "wantlist_matches": analysis.wantlist_matches,
            "collection_duplicates": analysis.collection_duplicates,
            "new_discoveries": analysis.new_discoveries,
            "completed_at": analysis.analysis_completed_at.isoformat() if analysis.analysis_completed_at else None,
        },
        "recommendations": formatted_recommendations,
        "seller_analyses": formatted_seller_analyses,
    }


@router.get("/search/{search_id}/multi-item-deals")
async def get_multi_item_deals(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get sellers with multiple items for potential shipping savings."""

    # Verify search belongs to user
    search_result = await db.execute(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == current_user.id)
    )
    search = search_result.scalar_one_or_none()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Get analysis
    analysis_result = await db.execute(select(SearchResultAnalysis).where(SearchResultAnalysis.search_id == search_id))
    analysis = analysis_result.scalar_one_or_none()

    if not analysis:
        return {
            "search_id": str(search_id),
            "multi_item_deals": [],
            "message": "Analysis not yet completed for this search",
        }

    # Get multi-item recommendations
    multi_item_recs_result = await db.execute(
        select(DealRecommendation)
        .where(
            DealRecommendation.analysis_id == analysis.id, DealRecommendation.recommendation_type == "MULTI_ITEM_DEAL"
        )
        .order_by(DealRecommendation.score_value.desc())
    )
    multi_item_recommendations = multi_item_recs_result.scalars().all()

    formatted_deals = []
    for rec in multi_item_recommendations:
        seller_result = await db.execute(select(Seller).where(Seller.id == rec.seller_id))
        seller = seller_result.scalar_one_or_none()

        formatted_deals.append(
            {
                "seller": {
                    "id": str(seller.id) if seller else None,
                    "name": seller.seller_name if seller else "Unknown",
                    "location": seller.location if seller else None,
                    "feedback_score": float(seller.feedback_score) if seller and seller.feedback_score else None,
                }
                if seller
                else None,
                "total_items": rec.total_items,
                "wantlist_items": rec.wantlist_items,
                "total_value": float(rec.total_value),
                "estimated_shipping": float(rec.estimated_shipping) if rec.estimated_shipping else None,
                "total_cost": float(rec.total_cost),
                "potential_savings": float(rec.potential_savings) if rec.potential_savings else None,
                "deal_score": rec.deal_score.value,
                "item_ids": rec.item_ids,
            }
        )

    return {
        "search_id": str(search_id),
        "multi_item_deals": formatted_deals,
    }


@router.get("/search/{search_id}/price-comparison")
async def get_price_comparison(
    search_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get price comparison data across platforms and sellers."""

    # Verify search belongs to user
    search_result = await db.execute(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == current_user.id)
    )
    search = search_result.scalar_one_or_none()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    # Get search results grouped by item match
    from src.models.item_match import ItemMatch
    from src.models.search import SearchResult

    results_query = await db.execute(
        select(SearchResult, ItemMatch, Seller)
        .outerjoin(ItemMatch, SearchResult.item_match_id == ItemMatch.id)
        .outerjoin(Seller, SearchResult.seller_id == Seller.id)
        .where(SearchResult.search_id == search_id)
        .order_by(SearchResult.item_price)
    )
    results = results_query.all()

    # Group by item match
    item_comparisons: dict[str, dict[str, Any]] = {}

    for search_result, item_match, seller in results:
        match_key = str(item_match.id) if item_match else f"unmatched_{search_result.id}"

        if match_key not in item_comparisons:
            item_comparisons[match_key] = {
                "item_match": {
                    "id": str(item_match.id) if item_match else None,
                    "canonical_title": item_match.canonical_title
                    if item_match
                    else search_result.item_data.get("title", "Unknown"),
                    "canonical_artist": item_match.canonical_artist
                    if item_match
                    else search_result.item_data.get("artist", "Unknown"),
                    "total_matches": item_match.total_matches if item_match else 1,
                }
                if item_match
                else {
                    "id": None,
                    "canonical_title": search_result.item_data.get("title", "Unknown"),
                    "canonical_artist": search_result.item_data.get("artist", "Unknown"),
                    "total_matches": 1,
                },
                "listings": [],
            }

        item_comparisons[match_key]["listings"].append(
            {
                "id": str(search_result.id),
                "platform": search_result.platform.value,
                "price": float(search_result.item_price) if search_result.item_price else None,
                "condition": search_result.item_condition,
                "seller": {
                    "id": str(seller.id) if seller else None,
                    "name": seller.seller_name if seller else "Unknown",
                    "location": seller.location if seller else None,
                    "feedback_score": float(seller.feedback_score) if seller and seller.feedback_score else None,
                }
                if seller
                else None,
                "is_in_wantlist": search_result.is_in_wantlist,
                "is_in_collection": search_result.is_in_collection,
            }
        )

    # Sort listings within each item by price
    for item_data in item_comparisons.values():
        item_data["listings"].sort(key=lambda x: x["price"] if x["price"] is not None else float("inf"))

    return {
        "search_id": str(search_id),
        "price_comparisons": list(item_comparisons.values()),
    }
