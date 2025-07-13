"""Redis client for caching and temporary storage."""

import json
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: Redis[bytes] | None = None


async def get_redis() -> Redis[bytes]:
    """Get Redis client instance."""
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.from_url(
            str(settings.redis_url),
            encoding="utf-8",
            decode_responses=True,
        )

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class OAuthTokenStore:
    """Store OAuth request tokens temporarily in Redis."""

    PREFIX = "oauth:request:"
    TTL = 600  # 10 minutes

    def __init__(self, redis_client: Redis[bytes]) -> None:
        self.redis = redis_client

    async def store_request_token(
        self,
        state: str,
        user_id: str,
        request_token: str,
        request_token_secret: str,
        provider: str,
    ) -> None:
        """Store OAuth request token data."""
        key = f"{self.PREFIX}{state}"
        data = {
            "user_id": user_id,
            "request_token": request_token,
            "request_token_secret": request_token_secret,
            "provider": provider,
        }

        await self.redis.setex(
            key,
            self.TTL,
            json.dumps(data),
        )
        logger.debug(f"Stored OAuth request token for state: {state}")

    async def get_request_token(self, state: str) -> dict[str, Any] | None:
        """Retrieve OAuth request token data."""
        key = f"{self.PREFIX}{state}"
        data = await self.redis.get(key)

        if data:
            logger.debug(f"Retrieved OAuth request token for state: {state}")
            return json.loads(data)  # type: ignore[no-any-return]

        logger.warning(f"No OAuth request token found for state: {state}")
        return None

    async def delete_request_token(self, state: str) -> None:
        """Delete OAuth request token data."""
        key = f"{self.PREFIX}{state}"
        await self.redis.delete(key)
        logger.debug(f"Deleted OAuth request token for state: {state}")
