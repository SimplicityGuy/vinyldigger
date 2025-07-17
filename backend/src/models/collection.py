from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.search import SearchPlatform

if TYPE_CHECKING:
    from src.models.collection_item import CollectionItem, WantListItem
    from src.models.user import User


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(
        SQLEnum(SearchPlatform, create_type=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    platform_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_count: Mapped[int] = mapped_column(default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="collections")
    items: Mapped[list[CollectionItem]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "platform", name="collections_user_id_platform_key"),)


class WantList(Base):
    __tablename__ = "want_lists"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    platform: Mapped[SearchPlatform] = mapped_column(
        SQLEnum(SearchPlatform, create_type=False, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    item_count: Mapped[int] = mapped_column(default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="want_lists")
    items: Mapped[list[WantListItem]] = relationship(
        "WantListItem", back_populates="want_list", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "platform", name="want_lists_user_id_platform_key"),)
