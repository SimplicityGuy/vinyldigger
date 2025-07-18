from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.api.v1.schemas.search_orchestration import (
    SavedSearchOrchestrationUpdate,
    SearchScheduleSuggestion,
)
from src.core.database import get_db
from src.models.search import SavedSearch, SearchPlatform, SearchResult
from src.models.user import User
from src.services.search import SearchService
from src.services.search_orchestrator import SearchOrchestrator

router = APIRouter()


class SavedSearchCreate(BaseModel):
    name: str
    query: str
    platform: SearchPlatform
    filters: dict[str, Any] = {}
    check_interval_hours: int = 24
    min_record_condition: str | None = None
    min_sleeve_condition: str | None = None
    seller_location_preference: str | None = None

    @field_validator("platform", mode="before")
    @classmethod
    def normalize_platform(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v


class SavedSearchUpdate(BaseModel):
    name: str | None = None
    query: str | None = None
    platform: SearchPlatform | None = None
    filters: dict[str, Any] | None = None
    check_interval_hours: int | None = None
    min_record_condition: str | None = None
    min_sleeve_condition: str | None = None
    seller_location_preference: str | None = None
    is_active: bool | None = None

    @field_validator("platform", mode="before")
    @classmethod
    def normalize_platform(cls, v: Any) -> Any:
        if v is not None and isinstance(v, str):
            return v.lower()
        return v


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    query: str
    platform: SearchPlatform
    filters: dict[str, Any]
    is_active: bool
    check_interval_hours: int
    last_run_at: str | None
    created_at: str
    updated_at: str
    min_record_condition: str | None
    min_sleeve_condition: str | None
    seller_location_preference: str | None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("last_run_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v: datetime | str | None) -> str | None:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_datetimes_to_str(cls, v: datetime | str) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


class SearchResultResponse(BaseModel):
    id: str
    platform: SearchPlatform
    item_id: str
    item_data: dict[str, Any]
    is_in_collection: bool
    is_in_wantlist: bool
    created_at: str

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str) -> str:
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v: datetime | str) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)


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
        min_record_condition=search_data.min_record_condition,
        min_sleeve_condition=search_data.min_sleeve_condition,
        seller_location_preference=search_data.seller_location_preference,
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


@router.put("/{search_id}", response_model=SavedSearchResponse)
async def update_search(
    search_id: UUID,
    search_data: SavedSearchUpdate,
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

    # Update only the fields that were provided
    update_data = search_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(search, field, value)

    await db.commit()
    await db.refresh(search)
    return search


@router.delete("/{search_id}")
async def delete_search(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
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
    except HTTPException as http_ex:
        # Re-raise HTTPException without wrapping it
        await db.rollback()
        raise http_ex
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete search: {str(e)}",
        ) from e


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

    # Get results, filtering out collection items and prioritizing wantlist items
    result = await db.execute(
        select(SearchResult)
        .where(
            SearchResult.search_id == search_id,
            ~SearchResult.is_in_collection,  # Exclude items already in collection
        )
        .order_by(
            SearchResult.is_in_wantlist.desc(),  # Wantlist items first
            SearchResult.created_at.desc(),  # Then by recency
        )
        .limit(100)
    )
    return list(result.scalars().all())


# Search Orchestration Endpoints

orchestrator = SearchOrchestrator()


@router.put("/{search_id}/orchestration", response_model=SavedSearchResponse)
async def update_search_orchestration(
    search_id: UUID,
    orchestration_data: SavedSearchOrchestrationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SavedSearch:
    """Update orchestration settings for a search."""
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

    # Update orchestration fields
    update_data = orchestration_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(search, field):
            setattr(search, field, value)

    await db.commit()
    return search


@router.get("/{search_id}/schedule-suggestion", response_model=SearchScheduleSuggestion)
async def get_schedule_suggestion(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SearchScheduleSuggestion:
    """Get scheduling suggestions for a search."""
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

    # Generate suggestions based on current settings
    current_schedule = f"Every {search.check_interval_hours} hours"

    suggested_times = []
    reasoning = "Based on your search patterns"
    estimated_improvement = "Potentially better results"

    # Add some intelligent suggestions
    if search.optimal_run_times:
        suggested_times = search.optimal_run_times
        reasoning = "Using your preferred run times"
    else:
        # Suggest common optimal times (morning, evening)
        suggested_times = [9, 18, 22]  # 9 AM, 6 PM, 10 PM
        reasoning = "Peak marketplace activity times"

    if search.check_interval_hours > 24:
        estimated_improvement = "More frequent checks may find better deals"
    elif search.check_interval_hours < 12:
        estimated_improvement = "Less frequent checks may reduce costs"

    return SearchScheduleSuggestion(
        current_schedule=current_schedule,
        suggested_times=suggested_times,
        reasoning=reasoning,
        estimated_improvement=estimated_improvement,
    )


@router.get("/{search_id}/dependencies", response_model=list[SavedSearchResponse])
async def get_search_dependencies(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[SavedSearch]:
    """Get all searches that depend on this search."""
    # Verify the search exists and belongs to the user
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

    # Get dependent searches
    dependent_searches = await orchestrator.get_dependent_searches(db, search_id)
    return dependent_searches


@router.post("/{search_id}/trigger", response_model=dict[str, Any])
async def trigger_search_manually(
    search_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually trigger a search execution."""
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

    if not search.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot trigger inactive search",
        )

    # Check budget constraints if applicable
    if search.budget_id:
        budget_ok = await orchestrator.check_budget_constraints(db, current_user.id, search.estimated_cost_per_result)
        if not budget_ok:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient budget to run search",
            )

    # Queue the search task
    search_service = SearchService()
    await search_service.queue_search(search.id, current_user.id)

    return {
        "message": f"Search '{search.name}' queued for execution",
        "search_id": search.id,
    }
