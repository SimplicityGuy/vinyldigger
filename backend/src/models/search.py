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
    from src.models.user import User


class SearchPlatform(str, Enum):
    EBAY = "EBAY"
    DISCOGS = "DISCOGS"
    BOTH = "BOTH"


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(SQLEnum(SearchPlatform, create_type=False), nullable=False)
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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="saved_searches")
    results: Mapped[list[SearchResult]] = relationship(
        "SearchResult", back_populates="search", cascade="all, delete-orphan"
    )


class SearchResult(Base):
    __tablename__ = "search_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    search_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("saved_searches.id"), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(SQLEnum(SearchPlatform, create_type=False), nullable=False)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    item_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_in_collection: Mapped[bool] = mapped_column(default=False)
    is_in_wantlist: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    search: Mapped[SavedSearch] = relationship("SavedSearch", back_populates="results")
