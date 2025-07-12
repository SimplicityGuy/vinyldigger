from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.app_config import OAuthProvider

if TYPE_CHECKING:
    from src.models.user import User


class OAuthToken(Base):
    """User-specific OAuth tokens obtained after authorization.

    This table stores the access tokens and secrets for each user
    after they've authorized the application.
    """

    __tablename__ = "oauth_tokens"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider: Mapped[OAuthProvider] = mapped_column(SQLEnum(OAuthProvider, create_type=False), nullable=False)

    # OAuth 1.0a tokens (Discogs)
    access_token: Mapped[str] = mapped_column(String(5000), nullable=False)
    access_token_secret: Mapped[str | None] = mapped_column(String(5000), nullable=True)

    # OAuth 2.0 tokens (eBay, future use)
    refresh_token: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional user info from the provider
    provider_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="oauth_tokens")

    # Unique constraint to ensure one token per user per provider
    __table_args__ = (UniqueConstraint("user_id", "provider", name="unique_user_provider"),)
