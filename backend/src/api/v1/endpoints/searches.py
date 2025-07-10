from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.user import User
from src.services.search import SearchService

router = APIRouter()


class SavedSearchCreate(BaseModel):
    name: str
    query: str
    platform: SearchPlatform
    filters: dict[str, Any] = {}
    check_interval_hours: int = 24


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    query: str
    platform: SearchPlatform
    filters: dict[str, Any]
    is_active: bool
    check_interval_hours: int
    last_checked_at: str | None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("last_checked_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v: datetime | str | None) -> str | None:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True


class SearchResultResponse(BaseModel):
    id: str
    platform: SearchPlatform
    item_id: str
    item_data: dict[str, Any]
    is_in_collection: bool
    is_in_wantlist: bool
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=SavedSearchResponse)
async def create_search(
    search_data: SavedSearchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SavedSearch:
    search = SavedSearch(
        user_id=current_user.id,
        name=search_data.name,
        query=search_data.query,
        platform=search_data.platform,
        filters=search_data.filters,
        check_interval_hours=search_data.check_interval_hours,
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)
    return search


@router.get("", response_model=list[SavedSearchResponse])
async def get_searches(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[SavedSearch]:
    result = await db.execute(select(SavedSearch).where(SavedSearch.user_id == current_user.id))
    return list(result.scalars().all())


@router.get("/{search_id}", response_model=SavedSearchResponse)
async def get_search(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SavedSearch:
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )
    return search


@router.delete("/{search_id}")
async def delete_search(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )

    await db.delete(search)
    await db.commit()
    return {"message": "Search deleted successfully"}


@router.post("/{search_id}/run")
async def run_search(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )

    # Queue the search task
    search_service = SearchService()
    await search_service.queue_search(search_id, current_user.id)

    return {"message": "Search queued successfully"}


@router.get("/{search_id}/results", response_model=list[SearchResultResponse])
async def get_search_results(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[SearchResult]:
    # Verify search belongs to user
    search_result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id,
        )
    )
    if not search_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found",
        )

    # Get results
    result = await db.execute(
        select(SearchResult)
        .where(SearchResult.search_id == search_id)
        .order_by(SearchResult.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())
