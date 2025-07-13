"""Item matching models for cross-platform item identification."""

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
    from src.models.search import SearchResult


class MatchConfidence(str, Enum):
    """Confidence levels for item matches."""

    EXACT = "EXACT"  # 95-100% - Catalog number or exact metadata match
    HIGH = "HIGH"  # 85-94%  - Strong title/artist/year match
    MEDIUM = "MEDIUM"  # 70-84%  - Good fuzzy match
    LOW = "LOW"  # 50-69%  - Weak match, manual review needed
    UNCERTAIN = "UNCERTAIN"  # <50%   - Very low confidence


class ItemMatch(Base):
    """Cross-platform item matching for price comparison."""

    __tablename__ = "item_matches"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Core item identification
    canonical_title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_artist: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_year: Mapped[int | None] = mapped_column(nullable=True)
    canonical_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    catalog_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Matching metadata
    discogs_release_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_fingerprint: Mapped[str] = mapped_column(String(500), nullable=False, index=True)  # Hash for quick lookup

    # Quality metrics
    total_matches: Mapped[int] = mapped_column(default=0)
    avg_confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    search_results: Mapped[list[SearchResult]] = relationship("SearchResult", back_populates="item_match")
    match_results: Mapped[list[ItemMatchResult]] = relationship(
        "ItemMatchResult", back_populates="item_match", cascade="all, delete-orphan"
    )


class ItemMatchResult(Base):
    """Individual search results matched to a canonical item."""

    __tablename__ = "item_match_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_match_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("item_matches.id"), nullable=False)
    search_result_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("search_results.id"), nullable=False
    )

    # Match quality
    confidence: Mapped[MatchConfidence] = mapped_column(SQLEnum(MatchConfidence, create_type=False), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # 0.00-100.00

    # Matching factors
    title_similarity: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    artist_similarity: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    year_match: Mapped[bool] = mapped_column(default=False)
    catalog_match: Mapped[bool] = mapped_column(default=False)
    format_match: Mapped[bool] = mapped_column(default=False)

    # Manual review flags
    requires_review: Mapped[bool] = mapped_column(default=False)
    reviewed_by_user: Mapped[bool] = mapped_column(default=False)
    user_confirmed: Mapped[bool | None] = mapped_column(nullable=True)  # True/False/None for pending

    # Additional matching metadata
    match_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item_match: Mapped[ItemMatch] = relationship("ItemMatch", back_populates="match_results")
    search_result: Mapped[SearchResult] = relationship("SearchResult")
