from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

if TYPE_CHECKING:
    pass


class OAuthProvider(str, Enum):
    DISCOGS = "discogs"
    EBAY = "ebay"


class AppConfig(Base):
    """Application-wide configuration for OAuth providers.

    This table stores the consumer/client credentials for OAuth providers.
    Only administrators should be able to modify these values.
    """

    __tablename__ = "app_config"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[OAuthProvider] = mapped_column(SQLEnum(OAuthProvider), unique=True, nullable=False)
    consumer_key: Mapped[str] = mapped_column(String(500), nullable=False)
    consumer_secret: Mapped[str] = mapped_column(String(500), nullable=False)

    # OAuth 1.0a specific fields (for Discogs)
    callback_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # OAuth 2.0 specific fields (for eBay, future use)
    redirect_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
