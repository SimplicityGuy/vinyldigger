"""Tests for multi-item deal recommendations."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import (
    DealRecommendation,
    RecommendationType,
    SellerAnalysis,
)
from src.models.seller import Seller
from src.models.user import User
from src.services.recommendation_engine import RecommendationEngine


@pytest.mark.asyncio
async def test_multi_item_recommendation_creation(db_session: AsyncSession):
    """Test creating multi-item deal recommendations."""
    # Create test user
    user = User(email="test_recommendations@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Pink Floyd Search",
        query="Pink Floyd",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create a seller with multiple items
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="vinylmaster",
        seller_name="Vinyl Master",
        feedback_score=99.5,
        total_feedback_count=1000,
        location="United States",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create multiple search results from same seller
    search_results = []
    for i in range(4):
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=f"item_{i}",
            seller_id=seller.id,
            item_data={
                "title": f"Pink Floyd - Album {i}",
                "condition": "Near Mint (NM or M-)",
                "price": {"value": f"{25 + i * 5}", "currency": "USD"},
            },
            item_price=Decimal(f"{25 + i * 5}.00"),
            is_in_wantlist=(i < 2),  # First 2 are in wantlist
            is_in_collection=(i == 3),  # Last one is in collection
        )
        search_results.append(result)
        db_session.add(result)

    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Verify analysis was created
    assert analysis is not None
    assert analysis.total_results == 4
    assert analysis.wantlist_matches == 2
    assert analysis.collection_duplicates == 1
    assert analysis.multi_item_sellers == 1

    # Get seller analysis
    from sqlalchemy import select

    seller_analyses = await db_session.execute(
        select(SellerAnalysis).where(SellerAnalysis.search_analysis_id == analysis.id)
    )
    seller_analysis = seller_analyses.scalars().first()

    assert seller_analysis is not None
    assert seller_analysis.total_items == 4
    assert seller_analysis.wantlist_items == 2
    assert seller_analysis.collection_duplicates == 1

    # Get recommendations
    recommendations = await db_session.execute(
        select(DealRecommendation).where(DealRecommendation.analysis_id == analysis.id)
    )
    recs = list(recommendations.scalars().all())

    # Should have at least one multi-item recommendation
    multi_item_recs = [r for r in recs if r.recommendation_type == RecommendationType.MULTI_ITEM_DEAL]
    assert len(multi_item_recs) > 0

    # Verify multi-item recommendation details
    rec = multi_item_recs[0]
    assert rec.seller_id == seller.id
    assert rec.total_items == 4
    assert rec.wantlist_items == 2
    assert rec.total_value == Decimal("130.00")  # Sum of all 4 items (25+30+35+40)
    assert len(rec.item_ids) == 3  # Excludes collection duplicate
    assert "2 want list items" in rec.description
    assert "plus 1 other records" in rec.description


@pytest.mark.asyncio
async def test_multi_item_recommendation_no_wantlist(db_session: AsyncSession):
    """Test multi-item recommendations when no wantlist items present."""
    # Create test user
    user = User(email="test_no_wantlist@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Beatles Search",
        query="Beatles",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create a seller with multiple items
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="beatlesfan",
        seller_name="Beatles Fan",
        feedback_score=98.0,
        total_feedback_count=500,
        location="United Kingdom",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create multiple search results - none in wantlist
    search_results = []
    for i in range(3):
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=f"beatles_{i}",
            seller_id=seller.id,
            item_data={
                "title": f"Beatles - Album {i}",
                "condition": "Very Good Plus (VG+)",
                "price": {"value": f"{20 + i * 3}", "currency": "USD"},
            },
            item_price=Decimal(f"{20 + i * 3}.00"),
            is_in_wantlist=False,
            is_in_collection=False,
        )
        search_results.append(result)
        db_session.add(result)

    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Get recommendations
    recommendations = await db_session.execute(
        select(DealRecommendation).where(DealRecommendation.analysis_id == analysis.id)
    )
    recs = list(recommendations.scalars().all())

    # Should have multi-item recommendation even without wantlist items
    multi_item_recs = [r for r in recs if r.recommendation_type == RecommendationType.MULTI_ITEM_DEAL]
    assert len(multi_item_recs) > 0

    rec = multi_item_recs[0]
    assert rec.wantlist_items == 0
    assert rec.total_items == 3
    assert "3 records you don't own" in rec.description
    assert "from one seller" in rec.description
    assert "Save $" in rec.recommendation_reason
    assert "shipping" in rec.recommendation_reason


@pytest.mark.asyncio
async def test_multi_item_recommendation_shipping_savings(db_session: AsyncSession):
    """Test that shipping savings are calculated for multi-item deals."""
    # Create test user
    user = User(email="test_shipping@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Jazz Search",
        query="Miles Davis",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create a seller
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="jazzlover",
        seller_name="Jazz Lover",
        feedback_score=97.5,
        total_feedback_count=250,
        location="Canada",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create 5 items from same seller
    for i in range(5):
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=f"jazz_{i}",
            seller_id=seller.id,
            item_data={
                "title": f"Miles Davis - Album {i}",
                "condition": "Very Good (VG)",
                "price": {"value": "15", "currency": "USD"},
            },
            item_price=Decimal("15.00"),
            is_in_wantlist=(i < 3),  # First 3 in wantlist
            is_in_collection=False,
        )
        db_session.add(result)

    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Get multi-item recommendation
    recommendations = await db_session.execute(
        select(DealRecommendation).where(
            DealRecommendation.analysis_id == analysis.id,
            DealRecommendation.recommendation_type == RecommendationType.MULTI_ITEM_DEAL,
        )
    )
    rec = recommendations.scalars().first()

    assert rec is not None
    assert rec.total_items == 5
    assert rec.wantlist_items == 3
    assert rec.potential_savings is not None
    assert rec.potential_savings > Decimal("0.00")  # Should have shipping savings
    assert rec.estimated_shipping is not None

    # Verify the recommendation reason mentions savings
    assert "Save $" in rec.recommendation_reason
    assert "shipping" in rec.recommendation_reason
    assert "5 items together" in rec.recommendation_reason


@pytest.mark.asyncio
async def test_no_multi_item_recommendation_single_item(db_session: AsyncSession):
    """Test that no multi-item recommendation is created for single-item sellers."""
    # Create test user
    user = User(email="test_single@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Rare Search",
        query="Rare Record",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create multiple sellers, each with only one item
    for i in range(3):
        seller = Seller(
            platform=SearchPlatform.DISCOGS,
            platform_seller_id=f"seller_{i}",
            seller_name=f"Seller {i}",
            feedback_score=95.0 + i,
            total_feedback_count=100 + i * 50,
            location="Germany",
        )
        db_session.add(seller)
        await db_session.commit()

        # Add single item from this seller
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=f"single_{i}",
            seller_id=seller.id,
            item_data={
                "title": f"Rare Record - Version {i}",
                "condition": "Good (G)",
                "price": {"value": "50", "currency": "USD"},
            },
            item_price=Decimal("50.00"),
            is_in_wantlist=True,
            is_in_collection=False,
        )
        db_session.add(result)

    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Get recommendations
    recommendations = await db_session.execute(
        select(DealRecommendation).where(DealRecommendation.analysis_id == analysis.id)
    )
    recs = list(recommendations.scalars().all())

    # Should NOT have any multi-item recommendations
    multi_item_recs = [r for r in recs if r.recommendation_type == RecommendationType.MULTI_ITEM_DEAL]
    assert len(multi_item_recs) == 0

    # Should have other types of recommendations (best price, high feedback, etc.)
    assert len(recs) > 0
    assert all(r.recommendation_type != RecommendationType.MULTI_ITEM_DEAL for r in recs)
