from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.api_key import APIKey
    from src.models.collection import Collection, WantList
    from src.models.search import SavedSearch


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    discogs_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    api_keys: Mapped[list[APIKey]] = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    saved_searches: Mapped[list[SavedSearch]] = relationship(
        "SavedSearch", back_populates="user", cascade="all, delete-orphan"
    )
    collections: Mapped[list[Collection]] = relationship(
        "Collection", back_populates="user", cascade="all, delete-orphan"
    )
    want_lists: Mapped[list[WantList]] = relationship("WantList", back_populates="user", cascade="all, delete-orphan")
