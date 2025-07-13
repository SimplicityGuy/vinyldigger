"""Seller models for multi-platform seller tracking and analysis."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.search import SearchPlatform

if TYPE_CHECKING:
    from src.models.search import SearchResult


class Seller(Base):
    """Seller information across platforms."""

    __tablename__ = "sellers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[SearchPlatform] = mapped_column(SQLEnum(SearchPlatform, create_type=False), nullable=False)
    platform_seller_id: Mapped[str] = mapped_column(String(255), nullable=False)
    seller_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Contact and location info
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Reputation metrics
    feedback_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0.00-100.00
    total_feedback_count: Mapped[int | None] = mapped_column(nullable=True)
    positive_feedback_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Shipping preferences
    ships_internationally: Mapped[bool] = mapped_column(default=False)
    estimated_shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Additional metadata from platform
    seller_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    search_results: Mapped[list[SearchResult]] = relationship("SearchResult", back_populates="seller")
    inventory_items: Mapped[list[SellerInventory]] = relationship(
        "SellerInventory", back_populates="seller", cascade="all, delete-orphan"
    )


class SellerInventory(Base):
    """Track multiple items available from a single seller."""

    __tablename__ = "seller_inventory"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    seller_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)
    search_result_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("search_results.id"), nullable=False
    )

    # Item details for quick access
    item_title: Mapped[str] = mapped_column(String(500), nullable=False)
    item_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    item_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Want list matching
    is_in_wantlist: Mapped[bool] = mapped_column(default=False)
    wantlist_priority: Mapped[int | None] = mapped_column(nullable=True)  # 1-10 priority scale

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    seller: Mapped[Seller] = relationship("Seller", back_populates="inventory_items")
    search_result: Mapped[SearchResult] = relationship("SearchResult")
