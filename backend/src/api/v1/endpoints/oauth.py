import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from requests_oauthlib import OAuth1Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.core.database import get_db
from src.core.logging import get_logger
from src.core.redis_client import OAuthTokenStore, get_redis
from src.models import AppConfig, OAuthProvider, OAuthToken, User

router = APIRouter()
logger = get_logger(__name__)


class OAuthStatusResponse(BaseModel):
    provider: str
    is_configured: bool
    is_authorized: bool
    username: str | None = None


class DiscogsCallbackResponse(BaseModel):
    message: str
    username: str


@router.get("/status/{provider}", response_model=OAuthStatusResponse)
async def get_oauth_status(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OAuthStatusResponse:
    """Check if the user has authorized the application for a specific provider."""
    # Convert provider string to enum
    try:
        provider_enum = OAuthProvider(provider.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider: {provider}. Must be one of: DISCOGS, EBAY",
        ) from None

    # Check if app is configured
    app_config_result = await db.execute(select(AppConfig).where(AppConfig.provider == provider_enum))
    app_config = app_config_result.scalar_one_or_none()

    # Check if user has authorized
    token_result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == provider_enum,
        )
    )
    token = token_result.scalar_one_or_none()

    return OAuthStatusResponse(
        provider=provider_enum.value,
        is_configured=app_config is not None,
        is_authorized=token is not None,
        username=token.provider_username if token else None,
    )


@router.post("/authorize/{provider}")
async def initiate_oauth_flow(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Initiate the OAuth authorization flow for a provider."""
    # Convert provider string to enum
    try:
        provider_enum = OAuthProvider(provider.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider: {provider}. Must be one of: DISCOGS, EBAY",
        ) from None

    # Get app configuration
    app_config_result = await db.execute(select(AppConfig).where(AppConfig.provider == provider_enum))
    app_config = app_config_result.scalar_one_or_none()

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider_enum.value} OAuth is not configured. Please contact an administrator.",
        )

    if provider_enum == OAuthProvider.DISCOGS:
        # OAuth 1.0a flow for Discogs
        oauth = OAuth1Session(
            app_config.consumer_key,
            client_secret=app_config.consumer_secret,
            callback_uri=app_config.callback_url or "oob",  # Out-of-band for desktop apps
        )

        # Step 1: Get request token
        request_token_url = "https://api.discogs.com/oauth/request_token"
        try:
            fetch_response = oauth.fetch_request_token(request_token_url)
            request_token = fetch_response.get("oauth_token")
            request_token_secret = fetch_response.get("oauth_token_secret")

            # Store request token temporarily with user association
            # Include a random state parameter for additional security
            state = secrets.token_urlsafe(32)

            # Store in Redis
            redis_client = await get_redis()
            token_store = OAuthTokenStore(redis_client)
            await token_store.store_request_token(
                state=state,
                user_id=str(current_user.id),
                request_token=request_token,
                request_token_secret=request_token_secret,
                provider=provider_enum.value,
            )

            # Step 2: Get authorization URL
            authorization_url = oauth.authorization_url("https://discogs.com/oauth/authorize")

            # Add state parameter to the URL
            separator = "&" if "?" in authorization_url else "?"
            authorization_url = f"{authorization_url}{separator}state={state}"

            return {
                "authorization_url": authorization_url,
                "state": state,
            }

        except Exception as e:
            logger.error(f"Failed to initiate Discogs OAuth flow: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate OAuth flow. Please try again later.",
            ) from e

    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth flow for {provider_enum.value} is not implemented yet.",
        )


@router.get("/callback/discogs", response_model=DiscogsCallbackResponse)
async def discogs_oauth_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> DiscogsCallbackResponse:
    """Handle the OAuth callback from Discogs."""
    # Retrieve the request token from Redis
    redis_client = await get_redis()
    token_store = OAuthTokenStore(redis_client)
    token_data = await token_store.get_request_token(state)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    # Verify the oauth_token matches
    if token_data["request_token"] != oauth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth token mismatch.",
        )

    # Get app configuration
    app_result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.DISCOGS))
    app_config = app_result.scalar_one_or_none()

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discogs OAuth is not configured.",
        )

    try:
        # Step 3: Exchange request token for access token
        oauth = OAuth1Session(
            app_config.consumer_key,
            client_secret=app_config.consumer_secret,
            resource_owner_key=token_data["request_token"],
            resource_owner_secret=token_data["request_token_secret"],
            verifier=oauth_verifier,
        )

        access_token_url = "https://api.discogs.com/oauth/access_token"
        oauth_tokens = oauth.fetch_access_token(access_token_url)

        access_token = oauth_tokens.get("oauth_token")
        access_token_secret = oauth_tokens.get("oauth_token_secret")

        # Step 4: Get user information from Discogs
        oauth = OAuth1Session(
            app_config.consumer_key,
            client_secret=app_config.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        identity_response = oauth.get("https://api.discogs.com/oauth/identity")
        identity_response.raise_for_status()
        identity_data = identity_response.json()

        discogs_user_id = str(identity_data.get("id", ""))
        discogs_username = identity_data.get("username", "")

        # Store the access token in the database
        user_id = token_data["user_id"]

        # Check if token already exists
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == OAuthProvider.DISCOGS,
        )
        token_result = await db.execute(stmt)
        existing_token = token_result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.access_token_secret = access_token_secret
            existing_token.provider_user_id = discogs_user_id
            existing_token.provider_username = discogs_username
        else:
            # Create new token
            new_token = OAuthToken(
                user_id=user_id,
                provider=OAuthProvider.DISCOGS,
                access_token=access_token,
                access_token_secret=access_token_secret,
                provider_user_id=discogs_user_id,
                provider_username=discogs_username,
            )
            db.add(new_token)

        await db.commit()

        # Clean up temporary storage
        await token_store.delete_request_token(state)

        return DiscogsCallbackResponse(
            message="Successfully authorized Discogs access!",
            username=discogs_username,
        )

    except Exception as e:
        logger.error(f"Failed to complete Discogs OAuth flow: {str(e)}")
        # Clean up temporary storage
        redis_client = await get_redis()
        token_store = OAuthTokenStore(redis_client)
        await token_store.delete_request_token(state)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth flow. Please try again.",
        ) from e


class DiscogsVerifyRequest(BaseModel):
    state: str
    verification_code: str


@router.post("/verify/discogs", response_model=DiscogsCallbackResponse)
async def verify_discogs_oauth(
    verify_data: DiscogsVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> DiscogsCallbackResponse:
    """Complete Discogs OAuth flow with verification code (for out-of-band flow)."""
    # Retrieve the request token from Redis
    redis_client = await get_redis()
    token_store = OAuthTokenStore(redis_client)
    token_data = await token_store.get_request_token(verify_data.state)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please restart the authorization process.",
        )

    # Verify the user matches
    if token_data["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This authorization request belongs to a different user.",
        )

    # Get app configuration
    app_result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.DISCOGS))
    app_config = app_result.scalar_one_or_none()

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discogs OAuth is not configured.",
        )

    try:
        # Exchange request token for access token using the verification code
        oauth = OAuth1Session(
            app_config.consumer_key,
            client_secret=app_config.consumer_secret,
            resource_owner_key=token_data["request_token"],
            resource_owner_secret=token_data["request_token_secret"],
            verifier=verify_data.verification_code,
        )

        access_token_url = "https://api.discogs.com/oauth/access_token"
        oauth_tokens = oauth.fetch_access_token(access_token_url)

        access_token = oauth_tokens.get("oauth_token")
        access_token_secret = oauth_tokens.get("oauth_token_secret")

        # Get user information from Discogs
        oauth = OAuth1Session(
            app_config.consumer_key,
            client_secret=app_config.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        identity_response = oauth.get("https://api.discogs.com/oauth/identity")
        identity_response.raise_for_status()
        identity_data = identity_response.json()

        discogs_user_id = str(identity_data.get("id", ""))
        discogs_username = identity_data.get("username", "")

        # Store the access token in the database
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == OAuthProvider.DISCOGS,
        )
        token_result = await db.execute(stmt)
        existing_token = token_result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.access_token_secret = access_token_secret
            existing_token.provider_user_id = discogs_user_id
            existing_token.provider_username = discogs_username
        else:
            # Create new token
            new_token = OAuthToken(
                user_id=current_user.id,
                provider=OAuthProvider.DISCOGS,
                access_token=access_token,
                access_token_secret=access_token_secret,
                provider_user_id=discogs_user_id,
                provider_username=discogs_username,
            )
            db.add(new_token)

        await db.commit()

        # Clean up temporary storage
        await token_store.delete_request_token(verify_data.state)

        return DiscogsCallbackResponse(
            message="Successfully authorized Discogs access!",
            username=discogs_username,
        )

    except Exception as e:
        logger.error(f"Failed to complete Discogs OAuth verification: {str(e)}")
        # Clean up on error
        await token_store.delete_request_token(verify_data.state)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify authorization code. Please try again.",
        ) from e


@router.delete("/revoke/{provider}")
async def revoke_oauth_access(
    provider: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke OAuth access for a provider."""
    # Convert provider string to enum
    try:
        provider_enum = OAuthProvider(provider.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid provider: {provider}. Must be one of: DISCOGS, EBAY",
        ) from None

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == provider_enum,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No authorization found for {provider_enum.value}.",
        )

    await db.delete(token)
    await db.commit()

    return {"message": f"Successfully revoked {provider_enum.value} access."}
