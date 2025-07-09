from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.security import api_key_encryption
from src.models.api_key import APIKey, APIService

logger = get_logger(__name__)


class BaseAPIService(ABC):
    def __init__(self, service: APIService) -> None:
        self.service = service
        self.logger = logger

    async def get_api_credentials(self, db: AsyncSession, user_id: UUID) -> dict[str, str] | None:
        result = await db.execute(select(APIKey).where(APIKey.user_id == user_id, APIKey.service == self.service))
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        credentials = {"key": api_key_encryption.decrypt_key(api_key.encrypted_key)}

        if api_key.encrypted_secret:
            credentials["secret"] = api_key_encryption.decrypt_key(api_key.encrypted_secret)

        return credentials

    @abstractmethod
    async def search(self, query: str, filters: dict[str, Any], credentials: dict[str, str]) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def get_item_details(self, item_id: str, credentials: dict[str, str]) -> dict[str, Any] | None:
        pass

    def format_search_result(self, raw_item: dict[str, Any], platform: str) -> dict[str, Any]:
        return {
            "platform": platform,
            "item_id": str(raw_item.get("id", "")),
            "title": raw_item.get("title", ""),
            "price": raw_item.get("price", 0.0),
            "currency": raw_item.get("currency", "USD"),
            "condition": raw_item.get("condition", "Unknown"),
            "seller": raw_item.get("seller", {}),
            "url": raw_item.get("url", ""),
            "image_url": raw_item.get("image_url", ""),
            "location": raw_item.get("location", ""),
            "shipping": raw_item.get("shipping", {}),
            "raw_data": raw_item,
        }
