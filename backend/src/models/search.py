from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.item_match import ItemMatch
    from src.models.search_budget import SearchBudget
    from src.models.search_chain import SearchChainLink
    from src.models.seller import Seller
    from src.models.user import User


class SearchPlatform(str, Enum):
    EBAY = "ebay"
    DISCOGS = "discogs"
    BOTH = "both"


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(
        SQLEnum(SearchPlatform, create_type=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    check_interval_hours: Mapped[int] = mapped_column(default=24)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Search preferences
    min_record_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)  # VG, VG+, NM, M
    min_sleeve_condition: Mapped[str | None] = mapped_column(String(10), nullable=True)  # VG, VG+, NM, M
    seller_location_preference: Mapped[str | None] = mapped_column(String(10), nullable=True)  # US, EU, UK, ANY

    # Orchestration fields
    depends_on_search: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("saved_searches.id"), nullable=True
    )
    trigger_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Example: {"min_results": 5, "max_price": 100, "found_in_wantlist": True}

    # Budget awareness
    budget_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("search_budgets.id"), nullable=True)
    estimated_cost_per_result: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.10"))

    # Smart scheduling
    optimal_run_times: Mapped[list[int]] = mapped_column(JSON, default=list)  # Hours of day [9, 14, 20]
    avoid_run_times: Mapped[list[int]] = mapped_column(JSON, default=list)  # Hours to avoid [1, 2, 3]
    priority_level: Mapped[int] = mapped_column(default=5)  # 1-10 priority for scheduling

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="saved_searches")
    results: Mapped[list[SearchResult]] = relationship(
        "SearchResult", back_populates="search", cascade="all, delete-orphan"
    )

    # Orchestration relationships
    budget: Mapped[SearchBudget | None] = relationship("SearchBudget", back_populates="searches")
    chain_links: Mapped[list[SearchChainLink]] = relationship("SearchChainLink", back_populates="search")
    dependent_searches: Mapped[list[SavedSearch]] = relationship(
        "SavedSearch", remote_side=[id], back_populates="parent_search"
    )
    parent_search: Mapped[SavedSearch | None] = relationship(
        "SavedSearch", remote_side=[depends_on_search], back_populates="dependent_searches"
    )


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    search_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("saved_searches.id"), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(
        SQLEnum(SearchPlatform, create_type=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    item_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_in_collection: Mapped[bool] = mapped_column(default=False)
    is_in_wantlist: Mapped[bool] = mapped_column(default=False)

    # Enhanced analysis fields
    seller_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sellers.id"), nullable=True)
    item_match_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("item_matches.id"), nullable=True
    )

    # Quick access fields for analysis
    item_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    item_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    matching_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100 overall item appeal

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search: Mapped[SavedSearch] = relationship("SavedSearch", back_populates="results")
    seller: Mapped[Seller | None] = relationship("Seller", back_populates="search_results")
    item_match: Mapped[ItemMatch | None] = relationship("ItemMatch", back_populates="search_results")
