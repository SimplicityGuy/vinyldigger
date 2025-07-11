"""Collection and Want List Item models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.collection import Collection, WantList


class CollectionItem(Base):
    """Individual items in a user's collection."""

    __tablename__ = "collection_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    collection_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False)
    platform_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    catalog_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, name="metadata")
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    collection: Mapped[Collection] = relationship("Collection", back_populates="items")

    __table_args__ = (UniqueConstraint("collection_id", "platform_item_id"),)


class WantListItem(Base):
    """Individual items in a user's want list."""

    __tablename__ = "want_list_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    want_list_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("want_lists.id"), nullable=False)
    platform_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, name="metadata")
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    want_list: Mapped[WantList] = relationship("WantList", back_populates="items")

    __table_args__ = (UniqueConstraint("want_list_id", "platform_item_id"),)
