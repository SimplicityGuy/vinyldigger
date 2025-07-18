from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.models.user import User


class SearchTemplate(Base):
    """Template for creating searches with predefined patterns."""

    __tablename__ = "search_templates"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # "genre_deep_dive", "label_focus", etc.

    # Template data contains search configuration with parameter placeholders
    template_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Example: {"query": "{artist_name}", "filters": {"genre": "{genre}"}, "min_price": "{min_price}"}

    # Template metadata
    is_public: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    usage_count: Mapped[int] = mapped_column(default=0)

    # Template parameters definition
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Example: {"artist_name": {"type": "string", "required": True}, "genre": {"type": "string", "default": "jazz"}}

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator: Mapped[User | None] = relationship("User", back_populates="search_templates")
