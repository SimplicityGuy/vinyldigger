"""Recommendation engine for generating smart deal recommendations."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.search import SavedSearch, SearchResult
from src.models.search_analysis import (
    DealRecommendation,
    DealScore,
    RecommendationType,
    SearchResultAnalysis,
    SellerAnalysis,
)
from src.models.seller import Seller
from src.services.seller_analyzer import SellerAnalysisService

logger = get_logger(__name__)


class RecommendationEngine:
    """Engine for generating intelligent deal recommendations."""

    def __init__(self):
        self.seller_analyzer = SellerAnalysisService()

    # Scoring weights for overall deal quality
    SCORING_WEIGHTS = {
        "price_competitiveness": 0.35,  # How good is the price vs alternatives
        "inventory_depth": 0.25,  # Multiple items from same seller
        "seller_reputation": 0.20,  # Seller feedback and reliability
        "location_preference": 0.10,  # Preferred seller location
        "condition_value": 0.10,  # Condition vs price ratio
    }

    async def analyze_search_results(self, db: AsyncSession, search_id: str, user_id: str) -> SearchResultAnalysis:
        """Perform comprehensive analysis of search results."""

        # Get search details
        search_result = await db.execute(select(SavedSearch).where(SavedSearch.id == search_id))
        search = search_result.scalar_one_or_none()

        if not search:
            raise ValueError(f"Search {search_id} not found")

        # Get all search results
        results_query = await db.execute(select(SearchResult).where(SearchResult.search_id == search_id))
        search_results = list(results_query.scalars().all())

        # Calculate summary statistics
        total_results = len(search_results)
        wantlist_matches = sum(1 for r in search_results if r.is_in_wantlist)
        collection_duplicates = sum(1 for r in search_results if r.is_in_collection)
        new_discoveries = total_results - wantlist_matches - collection_duplicates

        # Price analysis
        prices = [r.item_price for r in search_results if r.item_price]
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        avg_price = sum(prices) / len(prices) if prices else None

        # Count unique sellers
        unique_sellers = len({r.seller_id for r in search_results if r.seller_id})

        # Find multi-item sellers
        multi_item_opportunities = await self.seller_analyzer.find_multi_item_opportunities(db, search_id, min_items=2)
        multi_item_sellers = len(multi_item_opportunities)

        # Create analysis record
        analysis = SearchResultAnalysis(
            search_id=search_id,
            total_results=total_results,
            total_sellers=unique_sellers,
            multi_item_sellers=multi_item_sellers,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            wantlist_matches=wantlist_matches,
            collection_duplicates=collection_duplicates,
            new_discoveries=new_discoveries,
        )

        db.add(analysis)
        await db.flush()

        # Analyze individual sellers
        await self._analyze_sellers(db, analysis, search_results, search, user_id)

        # Generate recommendations
        await self._generate_recommendations(db, analysis, search, user_id)

        # Mark analysis as complete
        from datetime import datetime

        analysis.analysis_completed_at = datetime.utcnow()

        logger.info(
            f"Analysis completed for search {search_id}: "
            f"{total_results} results, {unique_sellers} sellers, "
            f"{multi_item_sellers} multi-item opportunities"
        )

        return analysis

    async def _analyze_sellers(
        self,
        db: AsyncSession,
        analysis: SearchResultAnalysis,
        search_results: list[SearchResult],
        search: SavedSearch,
        user_id: str,
    ) -> None:
        """Analyze individual sellers within the search."""

        # Group results by seller
        seller_results: dict[str, list[SearchResult]] = {}
        for result in search_results:
            if result.seller_id:
                seller_id_str = str(result.seller_id)
                if seller_id_str not in seller_results:
                    seller_results[seller_id_str] = []
                seller_results[seller_id_str].append(result)

        seller_analyses = []

        for seller_id, results in seller_results.items():
            # Get seller info
            seller_result = await db.execute(select(Seller).where(Seller.id == seller_id))
            seller = seller_result.scalar_one_or_none()

            if not seller:
                continue

            # Calculate seller metrics
            total_items = len(results)
            wantlist_items = sum(1 for r in results if r.is_in_wantlist)
            collection_duplicates = sum(1 for r in results if r.is_in_collection)

            # Value analysis
            valid_prices = [r.item_price for r in results if r.item_price]
            total_value = sum(valid_prices) if valid_prices else Decimal("0.00")
            avg_item_price = total_value / len(valid_prices) if valid_prices else Decimal("0.00")

            # Estimate shipping
            estimated_shipping = self.seller_analyzer.estimate_shipping_cost(seller, user_id, total_items)

            # Calculate scoring factors
            price_competitiveness = await self._calculate_price_competitiveness(db, results, analysis)
            inventory_depth_score = self._calculate_inventory_depth_score(total_items, wantlist_items)
            seller_reputation_score = await self.seller_analyzer.score_seller_reputation(seller)
            location_preference_score = await self.seller_analyzer.calculate_location_preference_score(
                seller, search.seller_location_preference
            )

            # Calculate overall score
            overall_score = (
                price_competitiveness * Decimal(str(self.SCORING_WEIGHTS["price_competitiveness"]))
                + inventory_depth_score * Decimal(str(self.SCORING_WEIGHTS["inventory_depth"]))
                + seller_reputation_score * Decimal(str(self.SCORING_WEIGHTS["seller_reputation"]))
                + location_preference_score * Decimal(str(self.SCORING_WEIGHTS["location_preference"]))
            )

            # Create seller analysis
            seller_analysis = SellerAnalysis(
                search_analysis_id=analysis.id,
                seller_id=seller_id,
                total_items=total_items,
                wantlist_items=wantlist_items,
                collection_duplicates=collection_duplicates,
                total_value=total_value,
                avg_item_price=avg_item_price,
                estimated_shipping=estimated_shipping,
                price_competitiveness=price_competitiveness,
                inventory_depth_score=inventory_depth_score,
                seller_reputation_score=seller_reputation_score,
                location_preference_score=location_preference_score,
                overall_score=overall_score,
            )

            seller_analyses.append(seller_analysis)
            db.add(seller_analysis)

        # Assign rankings based on overall score
        seller_analyses.sort(key=lambda x: x.overall_score, reverse=True)
        for rank, seller_analysis in enumerate(seller_analyses, 1):
            seller_analysis.recommendation_rank = rank

    async def _calculate_price_competitiveness(
        self, db: AsyncSession, seller_results: list[SearchResult], analysis: SearchResultAnalysis
    ) -> Decimal:
        """Calculate how competitive this seller's prices are."""

        seller_prices = [r.item_price for r in seller_results if r.item_price]
        if not seller_prices:
            return Decimal("50.0")  # Neutral score for no price data

        seller_avg = sum(seller_prices) / len(seller_prices)
        market_avg = analysis.avg_price or seller_avg

        if market_avg == 0:
            return Decimal("50.0")

        # Calculate competitiveness: lower prices = higher score
        price_ratio = float(seller_avg) / float(market_avg)

        if price_ratio <= 0.8:  # 20% below market
            return Decimal("100.0")
        elif price_ratio <= 0.9:  # 10% below market
            return Decimal("85.0")
        elif price_ratio <= 1.0:  # At market price
            return Decimal("70.0")
        elif price_ratio <= 1.1:  # 10% above market
            return Decimal("50.0")
        elif price_ratio <= 1.2:  # 20% above market
            return Decimal("30.0")
        else:  # More than 20% above market
            return Decimal("10.0")

    def _calculate_inventory_depth_score(self, total_items: int, wantlist_items: int) -> Decimal:
        """Calculate score based on inventory depth and want list matches."""

        # Base score for multiple items
        if total_items == 1:
            base_score = Decimal("30.0")
        elif total_items == 2:
            base_score = Decimal("60.0")
        elif total_items >= 3:
            base_score = Decimal("80.0")
        else:
            base_score = Decimal("0.0")

        # Bonus for want list items
        wantlist_bonus = min(wantlist_items * 10, 20)  # Up to 20 bonus points

        return min(base_score + Decimal(str(wantlist_bonus)), Decimal("100.0"))

    async def _generate_recommendations(
        self, db: AsyncSession, analysis: SearchResultAnalysis, search: SavedSearch, user_id: str
    ) -> None:
        """Generate deal recommendations based on analysis."""

        # Get top seller analyses
        top_sellers_result = await db.execute(
            select(SellerAnalysis)
            .where(SellerAnalysis.search_analysis_id == analysis.id)
            .order_by(SellerAnalysis.overall_score.desc())
            .limit(10)
        )
        top_sellers = top_sellers_result.scalars().all()

        recommendations = []

        for seller_analysis in top_sellers:
            # Get seller and their items
            seller_result = await db.execute(select(Seller).where(Seller.id == seller_analysis.seller_id))
            seller = seller_result.scalar_one_or_none()

            if not seller:
                continue

            # Get seller's search results
            items_result = await db.execute(
                select(SearchResult).where(SearchResult.search_id == search.id, SearchResult.seller_id == seller.id)
            )
            seller_items = list(items_result.scalars().all())

            # Generate recommendations based on seller characteristics
            if seller_analysis.wantlist_items >= 2:
                # Multi-item want list deal
                recommendation = await self._create_multi_item_recommendation(
                    analysis, seller, seller_analysis, seller_items
                )
                recommendations.append(recommendation)

            elif seller_analysis.overall_score >= 85.0 and seller_analysis.total_items == 1:
                # Best single item deal
                recommendation = await self._create_best_price_recommendation(
                    analysis, seller, seller_analysis, seller_items
                )
                recommendations.append(recommendation)

            elif seller_analysis.seller_reputation_score >= 90.0:
                # High feedback seller
                recommendation = await self._create_high_feedback_recommendation(
                    analysis, seller, seller_analysis, seller_items
                )
                recommendations.append(recommendation)

            elif seller_analysis.location_preference_score >= 90.0:
                # Location preference match
                recommendation = await self._create_location_preference_recommendation(
                    analysis, seller, seller_analysis, seller_items
                )
                recommendations.append(recommendation)

        # Add recommendations to database
        for rec in recommendations:
            db.add(rec)

    async def _create_multi_item_recommendation(
        self,
        analysis: SearchResultAnalysis,
        seller: Seller,
        seller_analysis: SellerAnalysis,
        seller_items: list[SearchResult],
    ) -> DealRecommendation:
        """Create recommendation for multi-item deals."""

        wantlist_items = [item for item in seller_items if item.is_in_wantlist]
        total_cost = seller_analysis.total_value + (seller_analysis.estimated_shipping or Decimal("0.00"))

        # Calculate shipping savings
        savings = self.seller_analyzer.calculate_shipping_savings(len(seller_items), seller)

        deal_score = self._determine_deal_score(seller_analysis.overall_score)

        return DealRecommendation(
            analysis_id=analysis.id,
            seller_id=seller.id,
            recommendation_type=RecommendationType.MULTI_ITEM_DEAL,
            deal_score=deal_score,
            score_value=seller_analysis.overall_score,
            total_items=seller_analysis.total_items,
            wantlist_items=seller_analysis.wantlist_items,
            total_value=seller_analysis.total_value,
            estimated_shipping=seller_analysis.estimated_shipping,
            total_cost=total_cost,
            potential_savings=savings,
            title=f"Multi-Item Deal from {seller.seller_name}",
            description=(
                f"Get {len(wantlist_items)} want list items plus "
                f"{seller_analysis.total_items - len(wantlist_items)} other records from one seller"
            ),
            recommendation_reason=(
                f"Save ${savings:.2f} on shipping by buying {seller_analysis.total_items} items together"
            ),
            item_ids=[str(item.id) for item in seller_items],
        )

    async def _create_best_price_recommendation(
        self,
        analysis: SearchResultAnalysis,
        seller: Seller,
        seller_analysis: SellerAnalysis,
        seller_items: list[SearchResult],
    ) -> DealRecommendation:
        """Create recommendation for best price deals."""

        item = seller_items[0]  # Single item
        total_cost = seller_analysis.total_value + (seller_analysis.estimated_shipping or Decimal("0.00"))

        deal_score = self._determine_deal_score(seller_analysis.overall_score)

        return DealRecommendation(
            analysis_id=analysis.id,
            seller_id=seller.id,
            recommendation_type=RecommendationType.BEST_PRICE,
            deal_score=deal_score,
            score_value=seller_analysis.overall_score,
            total_items=1,
            wantlist_items=1 if item.is_in_wantlist else 0,
            total_value=seller_analysis.total_value,
            estimated_shipping=seller_analysis.estimated_shipping,
            total_cost=total_cost,
            title=f"Best Price: {item.item_data.get('title', 'Unknown Item')}",
            description=f"Excellent price from {seller.seller_name}",
            recommendation_reason=f"Competitive pricing with {seller_analysis.price_competitiveness:.0f}% price score",
            item_ids=[str(item.id)],
        )

    async def _create_high_feedback_recommendation(
        self,
        analysis: SearchResultAnalysis,
        seller: Seller,
        seller_analysis: SellerAnalysis,
        seller_items: list[SearchResult],
    ) -> DealRecommendation:
        """Create recommendation for highly-rated sellers."""

        total_cost = seller_analysis.total_value + (seller_analysis.estimated_shipping or Decimal("0.00"))
        deal_score = self._determine_deal_score(seller_analysis.overall_score)

        return DealRecommendation(
            analysis_id=analysis.id,
            seller_id=seller.id,
            recommendation_type=RecommendationType.HIGH_FEEDBACK,
            deal_score=deal_score,
            score_value=seller_analysis.overall_score,
            total_items=seller_analysis.total_items,
            wantlist_items=seller_analysis.wantlist_items,
            total_value=seller_analysis.total_value,
            estimated_shipping=seller_analysis.estimated_shipping,
            total_cost=total_cost,
            title=f"Highly Rated Seller: {seller.seller_name}",
            description=f"Excellent reputation with {seller_analysis.seller_reputation_score:.0f}% feedback score",
            recommendation_reason="Trusted seller with strong feedback history",
            item_ids=[str(item.id) for item in seller_items],
        )

    async def _create_location_preference_recommendation(
        self,
        analysis: SearchResultAnalysis,
        seller: Seller,
        seller_analysis: SellerAnalysis,
        seller_items: list[SearchResult],
    ) -> DealRecommendation:
        """Create recommendation for preferred location sellers."""

        total_cost = seller_analysis.total_value + (seller_analysis.estimated_shipping or Decimal("0.00"))
        deal_score = self._determine_deal_score(seller_analysis.overall_score)

        return DealRecommendation(
            analysis_id=analysis.id,
            seller_id=seller.id,
            recommendation_type=RecommendationType.LOCATION_PREFERENCE,
            deal_score=deal_score,
            score_value=seller_analysis.overall_score,
            total_items=seller_analysis.total_items,
            wantlist_items=seller_analysis.wantlist_items,
            total_value=seller_analysis.total_value,
            estimated_shipping=seller_analysis.estimated_shipping,
            total_cost=total_cost,
            title=f"Preferred Location: {seller.seller_name}",
            description=f"Seller from your preferred region ({seller.location})",
            recommendation_reason="Matches your location preference with lower shipping costs",
            item_ids=[str(item.id) for item in seller_items],
        )

    def _determine_deal_score(self, overall_score: Decimal) -> DealScore:
        """Determine deal score category based on overall score."""
        score = float(overall_score)

        if score >= 90.0:
            return DealScore.EXCELLENT
        elif score >= 80.0:
            return DealScore.VERY_GOOD
        elif score >= 70.0:
            return DealScore.GOOD
        elif score >= 60.0:
            return DealScore.FAIR
        else:
            return DealScore.POOR
