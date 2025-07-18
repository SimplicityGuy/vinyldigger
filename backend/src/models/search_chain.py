from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.search import SavedSearch
    from src.models.user import User


class SearchChain(Base):
    """Search chain for orchestrating multiple related searches."""

    __tablename__ = "search_chains"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="search_chains")
    links: Mapped[list[SearchChainLink]] = relationship(
        "SearchChainLink", back_populates="chain", cascade="all, delete-orphan", order_by="SearchChainLink.order_index"
    )


class SearchChainLink(Base):
    """Individual link in a search chain."""

    __tablename__ = "search_chain_links"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    chain_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("search_chains.id"), nullable=False)
    search_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("saved_searches.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(nullable=False)

    # Trigger conditions for this link
    trigger_condition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Example: {"min_results": 5, "max_price": 100, "found_in_wantlist": True}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chain: Mapped[SearchChain] = relationship("SearchChain", back_populates="links")
    search: Mapped[SavedSearch] = relationship("SavedSearch", back_populates="chain_links")
