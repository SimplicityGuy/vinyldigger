from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.user import User

router = APIRouter()


class PreferencesUpdate(BaseModel):
    min_record_condition: str | None = None
    min_sleeve_condition: str | None = None
    seller_location_preference: str | None = None
    check_interval_hours: int | None = None


class PreferencesResponse(BaseModel):
    min_record_condition: str
    min_sleeve_condition: str
    seller_location_preference: str
    check_interval_hours: int


@router.get("/preferences", response_model=PreferencesResponse)
async def get_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
) -> PreferencesResponse:
    # In a real implementation, these would be stored in the database
    # For now, return defaults
    return PreferencesResponse(
        min_record_condition="VG+",
        min_sleeve_condition="VG+",
        seller_location_preference="US",
        check_interval_hours=24,
    )


@router.put("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    preferences: PreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponse:
    # In a real implementation, these would be stored in the database
    # For now, just return the updated values with defaults
    return PreferencesResponse(
        min_record_condition=preferences.min_record_condition or "VG+",
        min_sleeve_condition=preferences.min_sleeve_condition or "VG+",
        seller_location_preference=preferences.seller_location_preference or "US",
        check_interval_hours=preferences.check_interval_hours or 24,
    )
