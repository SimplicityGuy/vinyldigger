"""Search result analysis and recommendation models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.search import SavedSearch
    from src.models.seller import Seller


class RecommendationType(str, Enum):
    """Types of deal recommendations."""

    BEST_PRICE = "BEST_PRICE"  # Single item with best price+shipping
    MULTI_ITEM_DEAL = "MULTI_ITEM_DEAL"  # Seller with multiple wantlist items
    CONDITION_VALUE = "CONDITION_VALUE"  # Better condition at slight price premium
    LOCATION_PREFERENCE = "LOCATION_PREFERENCE"  # Preferred seller location
    HIGH_FEEDBACK = "HIGH_FEEDBACK"  # Seller with excellent reputation


class DealScore(str, Enum):
    """Overall deal quality scores."""

    EXCELLENT = "EXCELLENT"  # 90-100 - Don't miss this deal
    VERY_GOOD = "VERY_GOOD"  # 80-89  - Great deal
    GOOD = "GOOD"  # 70-79  - Solid option
    FAIR = "FAIR"  # 60-69  - Consider if few alternatives
    POOR = "POOR"  # <60    - Look elsewhere


class SearchResultAnalysis(Base):
    """Analysis and scoring for search results with recommendations."""

    __tablename__ = "search_result_analyses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    search_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("saved_searches.id", ondelete="CASCADE"), nullable=False
    )

    # Analysis metadata
    total_results: Mapped[int] = mapped_column(default=0)
    total_sellers: Mapped[int] = mapped_column(default=0)
    multi_item_sellers: Mapped[int] = mapped_column(default=0)

    # Price analysis
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Summary statistics
    wantlist_matches: Mapped[int] = mapped_column(default=0)
    collection_duplicates: Mapped[int] = mapped_column(default=0)
    new_discoveries: Mapped[int] = mapped_column(default=0)

    # Analysis completion
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_version: Mapped[str] = mapped_column(String(50), default="1.0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search: Mapped[SavedSearch] = relationship("SavedSearch")
    recommendations: Mapped[list[DealRecommendation]] = relationship(
        "DealRecommendation", back_populates="analysis", cascade="all, delete-orphan"
    )
    seller_analyses: Mapped[list[SellerAnalysis]] = relationship(
        "SellerAnalysis", back_populates="search_analysis", cascade="all, delete-orphan"
    )


class DealRecommendation(Base):
    """Individual deal recommendations with scoring."""

    __tablename__ = "deal_recommendations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("search_result_analyses.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)

    # Recommendation details
    recommendation_type: Mapped[RecommendationType] = mapped_column(
        SQLEnum(RecommendationType, create_type=False), nullable=False
    )
    deal_score: Mapped[DealScore] = mapped_column(SQLEnum(DealScore, create_type=False), nullable=False)
    score_value: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # 0.00-100.00

    # Deal specifics
    total_items: Mapped[int] = mapped_column(default=1)
    wantlist_items: Mapped[int] = mapped_column(default=0)
    total_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_shipping: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Savings analysis
    potential_savings: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    savings_vs_individual: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Recommendation text
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(String(500), nullable=False)

    # Associated items (list of search_result_ids)
    item_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    analysis: Mapped[SearchResultAnalysis] = relationship("SearchResultAnalysis", back_populates="recommendations")
    seller: Mapped[Seller] = relationship("Seller")


class SellerAnalysis(Base):
    """Per-seller analysis within a search."""

    __tablename__ = "seller_analyses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    search_analysis_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("search_result_analyses.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)

    # Inventory analysis
    total_items: Mapped[int] = mapped_column(default=0)
    wantlist_items: Mapped[int] = mapped_column(default=0)
    collection_duplicates: Mapped[int] = mapped_column(default=0)

    # Value analysis
    total_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    avg_item_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_shipping: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Scoring factors
    price_competitiveness: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)  # 0-100
    inventory_depth_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)  # 0-100
    seller_reputation_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)  # 0-100
    location_preference_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)  # 0-100

    # Overall scoring
    overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)  # 0-100
    recommendation_rank: Mapped[int] = mapped_column(default=0)  # 1-N ranking within search

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search_analysis: Mapped[SearchResultAnalysis] = relationship(
        "SearchResultAnalysis", back_populates="seller_analyses"
    )
    seller: Mapped[Seller] = relationship("Seller")
