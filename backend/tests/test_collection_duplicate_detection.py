"""Tests for collection duplicate detection."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.search_analysis import DealRecommendation, RecommendationType, SellerAnalysis
from src.models.seller import Seller
from src.models.user import User
from src.services.recommendation_engine import RecommendationEngine


@pytest.mark.asyncio
async def test_collection_duplicate_detection(db_session: AsyncSession):
    """Test that collection duplicates are properly detected and excluded."""
    # Create test user
    user = User(email="test_duplicates@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Collection Check",
        query="test query",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create a seller
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="test_seller",
        seller_name="Test Seller",
        feedback_score=98.0,
        total_feedback_count=500,
        location="United States",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create search results with various collection statuses
    results = [
        # Item 1: In collection (duplicate)
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="item_1",
            seller_id=seller.id,
            item_data={
                "title": "Album 1",
                "condition": "Near Mint (NM or M-)",
                "price": {"value": "25", "currency": "USD"},
            },
            item_price=Decimal("25.00"),
            is_in_wantlist=False,
            is_in_collection=True,  # This is a collection duplicate
        ),
        # Item 2: In wantlist but not collection
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="item_2",
            seller_id=seller.id,
            item_data={
                "title": "Album 2",
                "condition": "Very Good Plus (VG+)",
                "price": {"value": "20", "currency": "USD"},
            },
            item_price=Decimal("20.00"),
            is_in_wantlist=True,
            is_in_collection=False,
        ),
        # Item 3: Neither in wantlist nor collection
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="item_3",
            seller_id=seller.id,
            item_data={"title": "Album 3", "condition": "Very Good (VG)", "price": {"value": "15", "currency": "USD"}},
            item_price=Decimal("15.00"),
            is_in_wantlist=False,
            is_in_collection=False,
        ),
        # Item 4: In collection AND wantlist (still a duplicate)
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="item_4",
            seller_id=seller.id,
            item_data={"title": "Album 4", "condition": "Good Plus (G+)", "price": {"value": "10", "currency": "USD"}},
            item_price=Decimal("10.00"),
            is_in_wantlist=True,
            is_in_collection=True,  # This is also a collection duplicate
        ),
    ]

    for result in results:
        db_session.add(result)
    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Verify analysis counts
    assert analysis.total_results == 4
    assert analysis.collection_duplicates == 2  # Items 1 and 4
    assert analysis.wantlist_matches == 2  # Items 2 and 4 (item 4 counts as both)
    assert analysis.new_discoveries == 1  # Only item 3

    # Get seller analysis
    from sqlalchemy import select

    seller_analyses = await db_session.execute(
        select(SellerAnalysis).where(SellerAnalysis.search_analysis_id == analysis.id)
    )
    seller_analysis = seller_analyses.scalars().first()

    assert seller_analysis is not None
    assert seller_analysis.total_items == 4
    assert seller_analysis.collection_duplicates == 2
    assert seller_analysis.wantlist_items == 2

    # Get recommendations
    recommendations = await db_session.execute(
        select(DealRecommendation).where(DealRecommendation.analysis_id == analysis.id)
    )
    recs = list(recommendations.scalars().all())

    # Check that recommendations exclude collection items
    for rec in recs:
        # Collection duplicates should not be included in item_ids
        assert "item_1" not in rec.item_ids
        assert "item_4" not in rec.item_ids
        # Non-collection items should be included
        if rec.item_ids:  # Some recommendations might not have specific items
            assert all(item_id in ["item_2", "item_3"] for item_id in rec.item_ids if item_id.startswith("item_"))


@pytest.mark.asyncio
async def test_search_results_endpoint_excludes_collection(db_session: AsyncSession):
    """Test that the search results endpoint excludes collection items."""
    from src.api.v1.endpoints.searches import get_search_results

    # Create test user
    user = User(email="test_endpoint@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id, name="Endpoint Test", query="test", platform=SearchPlatform.DISCOGS, filters={}, is_active=True
    )
    db_session.add(search)
    await db_session.commit()

    # Create mixed search results
    for i in range(5):
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=f"endpoint_item_{i}",
            item_data={"title": f"Album {i}", "price": {"value": "20", "currency": "USD"}},
            item_price=Decimal("20.00"),
            is_in_wantlist=(i % 2 == 0),  # Even items in wantlist
            is_in_collection=(i < 2),  # First 2 items in collection
        )
        db_session.add(result)
    await db_session.commit()

    # Call the endpoint function directly
    results = await get_search_results(search.id, user, db_session)

    # Should only get 3 results (items 2, 3, 4 - not in collection)
    assert len(results) == 3

    # Verify no collection items are included
    result_ids = [r.item_id for r in results]
    assert "endpoint_item_0" not in result_ids  # In collection
    assert "endpoint_item_1" not in result_ids  # In collection
    assert "endpoint_item_2" in result_ids  # Not in collection, in wantlist
    assert "endpoint_item_3" in result_ids  # Not in collection, not in wantlist
    assert "endpoint_item_4" in result_ids  # Not in collection, in wantlist

    # Verify wantlist items come first
    assert results[0].is_in_wantlist is True  # item_2
    assert results[1].is_in_wantlist is True  # item_4
    assert results[2].is_in_wantlist is False  # item_3


@pytest.mark.asyncio
async def test_collection_duplicate_price_exclusion(db_session: AsyncSession):
    """Test that collection duplicate prices are excluded from analysis."""
    # Create test user
    user = User(email="test_price_exclusion@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id, name="Price Test", query="test", platform=SearchPlatform.DISCOGS, filters={}, is_active=True
    )
    db_session.add(search)
    await db_session.commit()

    # Create seller
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="price_test_seller",
        seller_name="Price Test Seller",
        feedback_score=95.0,
        total_feedback_count=100,
        location="Japan",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create results with varying prices and collection status
    results = [
        # Very expensive item in collection (should not affect price analysis)
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="expensive_duplicate",
            seller_id=seller.id,
            item_data={"title": "Rare Collection Item", "price": {"value": "500", "currency": "USD"}},
            item_price=Decimal("500.00"),
            is_in_collection=True,
        ),
        # Normal priced items not in collection
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="normal_1",
            seller_id=seller.id,
            item_data={"title": "Normal Album 1", "price": {"value": "25", "currency": "USD"}},
            item_price=Decimal("25.00"),
            is_in_collection=False,
        ),
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="normal_2",
            seller_id=seller.id,
            item_data={"title": "Normal Album 2", "price": {"value": "30", "currency": "USD"}},
            item_price=Decimal("30.00"),
            is_in_collection=False,
        ),
        SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id="normal_3",
            seller_id=seller.id,
            item_data={"title": "Normal Album 3", "price": {"value": "35", "currency": "USD"}},
            item_price=Decimal("35.00"),
            is_in_collection=False,
        ),
    ]

    for result in results:
        db_session.add(result)
    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Price analysis should be based only on non-collection items
    # Average should be (25 + 30 + 35) / 3 = 30, not including the 500 item
    assert analysis.avg_price == Decimal("30.00")
    assert analysis.min_price == Decimal("25.00")
    assert analysis.max_price == Decimal("35.00")

    # Get seller analysis
    from sqlalchemy import select

    seller_analyses = await db_session.execute(
        select(SellerAnalysis).where(SellerAnalysis.search_analysis_id == analysis.id)
    )
    seller_analysis = seller_analyses.scalars().first()

    # Seller's total value should include all items
    assert seller_analysis is not None
    assert seller_analysis.total_value == Decimal("590.00")  # 500 + 25 + 30 + 35
    # But average price calculation should handle this appropriately
    assert seller_analysis.avg_item_price == Decimal("147.50")  # 590 / 4


@pytest.mark.asyncio
async def test_multi_item_recommendation_excludes_duplicates(db_session: AsyncSession):
    """Test that multi-item recommendations properly exclude collection duplicates."""
    # Create test user
    user = User(email="test_multi_exclude@example.com", hashed_password="hashed_password", is_active=True)
    db_session.add(user)
    await db_session.commit()

    # Create saved search
    search = SavedSearch(
        user_id=user.id,
        name="Multi Exclude Test",
        query="test",
        platform=SearchPlatform.DISCOGS,
        filters={},
        is_active=True,
    )
    db_session.add(search)
    await db_session.commit()

    # Create seller
    seller = Seller(
        platform=SearchPlatform.DISCOGS,
        platform_seller_id="multi_seller",
        seller_name="Multi Seller",
        feedback_score=99.0,
        total_feedback_count=1000,
        location="Netherlands",
    )
    db_session.add(seller)
    await db_session.commit()

    # Create 5 items: 2 collection duplicates, 2 wantlist, 1 new
    items = [
        ("dup_1", True, False, "25.00"),  # Collection duplicate
        ("want_1", False, True, "30.00"),  # Wantlist only
        ("dup_2", True, False, "35.00"),  # Collection duplicate
        ("want_2", False, True, "40.00"),  # Wantlist only
        ("new_1", False, False, "45.00"),  # New discovery
    ]

    for item_id, in_collection, in_wantlist, price in items:
        result = SearchResult(
            search_id=search.id,
            platform=SearchPlatform.DISCOGS,
            item_id=item_id,
            seller_id=seller.id,
            item_data={"title": f"Album {item_id}", "price": {"value": price, "currency": "USD"}},
            item_price=Decimal(price),
            is_in_collection=in_collection,
            is_in_wantlist=in_wantlist,
        )
        db_session.add(result)
    await db_session.commit()

    # Run recommendation engine
    engine = RecommendationEngine()
    analysis = await engine.analyze_search_results(db_session, str(search.id), str(user.id))

    # Get multi-item recommendation
    recommendations = await db_session.execute(
        select(DealRecommendation).where(DealRecommendation.analysis_id == analysis.id)
    )
    recs = list(recommendations.scalars().all())

    # Find multi-item recommendation
    multi_rec = next((r for r in recs if r.recommendation_type == RecommendationType.MULTI_ITEM_DEAL), None)
    assert multi_rec is not None

    # Should only include non-collection items (3 items)
    assert len(multi_rec.item_ids) == 3

    # Get the actual SearchResult objects to check
    from uuid import UUID

    result_ids = [UUID(rid) if isinstance(rid, str) else rid for rid in multi_rec.item_ids]
    included_item_ids = []
    for result_id in result_ids:
        result_query = await db_session.execute(select(SearchResult).where(SearchResult.id == result_id))
        search_result = result_query.scalar_one_or_none()
        if search_result:
            included_item_ids.append(search_result.item_id)

    # Check that the right items are included
    assert "want_1" in included_item_ids
    assert "want_2" in included_item_ids
    assert "new_1" in included_item_ids
    assert "dup_1" not in included_item_ids
    assert "dup_2" not in included_item_ids

    # Description should reflect correct counts
    assert "2 want list items" in multi_rec.description
    assert "3 records" in multi_rec.recommendation_reason or "3 items" in multi_rec.recommendation_reason
