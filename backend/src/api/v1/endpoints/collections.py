from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.collection import Collection, WantList
from src.models.user import User
from src.workers.tasks import sync_collection_task

router = APIRouter()


class CollectionResponse(BaseModel):
    id: str
    item_count: int
    last_sync_at: str | None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("last_sync_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v: datetime | str | None) -> str | None:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class WantListResponse(BaseModel):
    id: str
    item_count: int
    last_sync_at: str | None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("last_sync_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v: datetime | str | None) -> str | None:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


@router.post("/sync")
async def sync_all(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Queue sync task for both collection and want list
    sync_collection_task.delay(str(current_user.id))

    return {"message": "Collection and want list sync queued successfully"}


@router.post("/sync/collection")
async def sync_collection_only(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Queue sync task for collection only
    sync_collection_task.delay(str(current_user.id), sync_type="collection")

    return {"message": "Collection sync queued successfully"}


@router.post("/sync/wantlist")
async def sync_wantlist_only(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Queue sync task for want list only
    sync_collection_task.delay(str(current_user.id), sync_type="wantlist")

    return {"message": "Want list sync queued successfully"}


@router.get("/status", response_model=CollectionResponse)
async def get_collection_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    result = await db.execute(select(Collection).where(Collection.user_id == current_user.id))
    collection = result.scalar_one_or_none()
    if not collection:
        return CollectionResponse(id="", item_count=0, last_sync_at=None)
    return CollectionResponse(
        id=str(collection.id),
        item_count=collection.item_count,
        last_sync_at=collection.last_sync_at.isoformat() if collection.last_sync_at else None,
    )


@router.get("/wantlist/status", response_model=WantListResponse)
async def get_wantlist_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> WantListResponse:
    result = await db.execute(select(WantList).where(WantList.user_id == current_user.id))
    wantlist = result.scalar_one_or_none()
    if not wantlist:
        return WantListResponse(id="", item_count=0, last_sync_at=None)
    return WantListResponse(
        id=str(wantlist.id),
        item_count=wantlist.item_count,
        last_sync_at=wantlist.last_sync_at.isoformat() if wantlist.last_sync_at else None,
    )
