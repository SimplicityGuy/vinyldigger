from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.core.security import api_key_encryption
from src.models.api_key import APIKey, APIService
from src.models.user import User

router = APIRouter()


class APIKeyCreate(BaseModel):
    service: APIService
    key: str
    secret: str | None = None


class APIKeyResponse(BaseModel):
    id: str
    service: APIService
    created_at: str

    class Config:
        from_attributes = True


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


@router.put("/api-keys", response_model=APIKeyResponse)
async def update_api_key(
    api_key_data: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    # Check if API key already exists for this service
    result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == current_user.id,
            APIKey.service == api_key_data.service,
        )
    )
    existing_key = result.scalar_one_or_none()

    if existing_key:
        # Update existing key
        existing_key.encrypted_key = api_key_encryption.encrypt_key(api_key_data.key)
        if api_key_data.secret:
            existing_key.encrypted_secret = api_key_encryption.encrypt_key(
                api_key_data.secret
            )
        api_key = existing_key
    else:
        # Create new key
        api_key = APIKey(
            user_id=current_user.id,
            service=api_key_data.service,
            encrypted_key=api_key_encryption.encrypt_key(api_key_data.key),
            encrypted_secret=(
                api_key_encryption.encrypt_key(api_key_data.secret)
                if api_key_data.secret
                else None
            ),
        )
        db.add(api_key)

    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def get_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[APIKey]:
    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id))
    return list(result.scalars().all())


@router.delete("/api-keys/{service}")
async def delete_api_key(
    service: APIService,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == current_user.id,
            APIKey.service == service,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()
    return {"message": "API key deleted successfully"}


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
