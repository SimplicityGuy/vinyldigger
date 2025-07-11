from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models import AppConfig, OAuthProvider, User

router = APIRouter()


class AppConfigCreate(BaseModel):
    provider: OAuthProvider
    consumer_key: str
    consumer_secret: str
    callback_url: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v


class AppConfigResponse(BaseModel):
    provider: OAuthProvider
    consumer_key: str
    callback_url: str | None = None
    redirect_uri: str | None = None
    scope: str | None = None
    is_configured: bool = True


def require_admin(current_user: User) -> User:
    """Require the current user to be an admin."""
    # For now, we'll check if the user email ends with a specific domain
    # In production, you'd want a proper admin flag in the User model
    admin_domains = ["@admin.com", "@vinyldigger.com"]
    is_admin = any(current_user.email.endswith(domain) for domain in admin_domains)

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource.",
        )

    return current_user


@router.get("/app-config", response_model=list[AppConfigResponse])
async def list_app_configurations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[AppConfigResponse]:
    """List all OAuth provider configurations (admin only)."""
    require_admin(current_user)

    result = await db.execute(select(AppConfig))
    configs = result.scalars().all()

    return [
        AppConfigResponse(
            provider=config.provider,
            consumer_key=config.consumer_key[:10] + "..." if config.consumer_key else "",
            callback_url=config.callback_url,
            redirect_uri=config.redirect_uri,
            scope=config.scope,
        )
        for config in configs
    ]


@router.put("/app-config/{provider}", response_model=AppConfigResponse)
async def update_app_configuration(
    provider: str,
    config_data: AppConfigCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AppConfigResponse:
    """Create or update OAuth provider configuration (admin only)."""
    require_admin(current_user)

    # Convert provider string to enum
    try:
        provider_enum = OAuthProvider(provider.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider: {provider}. Must be one of: DISCOGS, EBAY",
        ) from None

    if provider_enum != config_data.provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider in URL must match provider in body.",
        )

    # Check if configuration already exists
    result = await db.execute(select(AppConfig).where(AppConfig.provider == provider_enum))
    existing_config = result.scalar_one_or_none()

    if existing_config:
        # Update existing configuration
        existing_config.consumer_key = config_data.consumer_key
        existing_config.consumer_secret = config_data.consumer_secret
        existing_config.callback_url = config_data.callback_url
        existing_config.redirect_uri = config_data.redirect_uri
        existing_config.scope = config_data.scope
        config = existing_config
    else:
        # Create new configuration
        config = AppConfig(
            provider=provider_enum,
            consumer_key=config_data.consumer_key,
            consumer_secret=config_data.consumer_secret,
            callback_url=config_data.callback_url,
            redirect_uri=config_data.redirect_uri,
            scope=config_data.scope,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return AppConfigResponse(
        provider=config.provider,
        consumer_key=config.consumer_key[:10] + "...",
        callback_url=config.callback_url,
        redirect_uri=config.redirect_uri,
        scope=config.scope,
    )


@router.delete("/app-config/{provider}")
async def delete_app_configuration(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete OAuth provider configuration (admin only)."""
    require_admin(current_user)

    # Convert provider string to enum
    try:
        provider_enum = OAuthProvider(provider.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider: {provider}. Must be one of: DISCOGS, EBAY",
        ) from None

    result = await db.execute(select(AppConfig).where(AppConfig.provider == provider_enum))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for {provider_enum.value} not found.",
        )

    await db.delete(config)
    await db.commit()

    return {"message": f"Configuration for {provider_enum.value} deleted successfully."}
