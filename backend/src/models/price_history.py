from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.search import SearchPlatform


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[SearchPlatform] = mapped_column(String(50), nullable=False)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sleeve_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seller_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
