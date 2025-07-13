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
from src.models import AppConfig, OAuthEnvironment, OAuthProvider, OAuthToken, User

router = APIRouter()
logger = get_logger(__name__)


def get_ebay_urls(app_config: AppConfig) -> dict[str, str]:
    """Determine the correct eBay URLs based on the configuration environment."""
    # First, try to detect environment from App ID
    is_sandbox = False
    if "SBX" in app_config.consumer_key.upper():
        is_sandbox = True
    elif "PRD" in app_config.consumer_key.upper():
        is_sandbox = False
    else:
        # Fall back to environment field (if available)
        is_sandbox = hasattr(app_config, "environment") and app_config.environment == OAuthEnvironment.SANDBOX

    if is_sandbox:
        return {
            "auth_url": "https://auth.sandbox.ebay.com/oauth2/authorize",
            "token_url": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
            "user_info_url": "https://apiz.sandbox.ebay.com/commerce/identity/v1/user",
            "default_scope": "https://api.ebay.com/oauth/api_scope",  # Scope is same for both
        }
    else:
        return {
            "auth_url": "https://auth.ebay.com/oauth2/authorize",
            "token_url": "https://api.ebay.com/identity/v1/oauth2/token",
            "user_info_url": "https://apiz.ebay.com/commerce/identity/v1/user",
            "default_scope": "https://api.ebay.com/oauth/api_scope",
        }


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
            if request_token and request_token_secret:
                await token_store.store_request_token(
                    state=state,
                    user_id=str(current_user.id),
                    request_token=request_token,
                    request_token_secret=request_token_secret,
                    provider=provider_enum.value,
                )
            else:
                raise HTTPException(status_code=400, detail="Failed to get request token from Discogs")

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

    elif provider_enum == OAuthProvider.EBAY:
        # OAuth 2.0 flow for eBay
        # Generate a state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state temporarily with user association
        redis_client = await get_redis()
        token_store = OAuthTokenStore(redis_client)
        await token_store.store_request_token(
            state=state,
            user_id=str(current_user.id),
            request_token="",  # Not used for OAuth2
            request_token_secret="",  # Not used for OAuth2
            provider=provider_enum.value,
        )

        # Get correct URLs for this environment
        ebay_urls = get_ebay_urls(app_config)

        # Build authorization URL
        params = {
            "client_id": app_config.consumer_key,
            "response_type": "code",
            "redirect_uri": app_config.redirect_uri or "urn:ietf:wg:oauth:2.0:oob",
            "scope": app_config.scope or ebay_urls["default_scope"],
            "state": state,
        }

        # Build query string
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{ebay_urls['auth_url']}?{query_string}"

        return {
            "authorization_url": authorization_url,
            "state": state,
        }
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

        if not access_token or not access_token_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Discogs.",
            )

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

        if not access_token or not access_token_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Discogs.",
            )

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


class EbayCallbackResponse(BaseModel):
    message: str
    username: str


@router.get("/callback/ebay", response_model=EbayCallbackResponse)
async def ebay_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> EbayCallbackResponse:
    """Handle the OAuth2 callback from eBay."""
    # Retrieve the state from Redis
    redis_client = await get_redis()
    token_store = OAuthTokenStore(redis_client)
    token_data = await token_store.get_request_token(state)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    # Get app configuration
    app_result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.EBAY))
    app_config = app_result.scalar_one_or_none()

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="eBay OAuth is not configured.",
        )

    try:
        # Get correct URLs for this environment
        ebay_urls = get_ebay_urls(app_config)

        # Exchange authorization code for access token
        import base64

        import httpx

        # Create Basic auth header
        auth_string = f"{app_config.consumer_key}:{app_config.consumer_secret}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                ebay_urls["token_url"],
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": app_config.redirect_uri or "urn:ietf:wg:oauth:2.0:oob",
                },
            )
            response.raise_for_status()

            token_data_response = response.json()
            access_token = token_data_response.get("access_token")
            refresh_token = token_data_response.get("refresh_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from eBay.",
                )

            # Get user information from eBay (optional - may fail in sandbox or with limited scope)
            ebay_user_id = ""
            ebay_username = ""
            try:
                user_response = await client.get(
                    ebay_urls["user_info_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                user_response.raise_for_status()
                user_data = user_response.json()
                ebay_user_id = user_data.get("userId", "")
                ebay_username = user_data.get("username", "")
            except Exception as user_info_error:
                logger.warning(f"Could not retrieve eBay user info (continuing without it): {str(user_info_error)}")
                # Continue without user info - this is common in sandbox or with limited scopes

        # Store the access token in the database
        user_id = token_data["user_id"]

        # Check if token already exists
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == OAuthProvider.EBAY,
        )
        token_result = await db.execute(stmt)
        existing_token = token_result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.refresh_token = refresh_token
            existing_token.provider_user_id = ebay_user_id
            existing_token.provider_username = ebay_username
        else:
            # Create new token
            new_token = OAuthToken(
                user_id=user_id,
                provider=OAuthProvider.EBAY,
                access_token=access_token,
                refresh_token=refresh_token,
                provider_user_id=ebay_user_id,
                provider_username=ebay_username,
            )
            db.add(new_token)

        await db.commit()

        # Clean up temporary storage
        await token_store.delete_request_token(state)

        return EbayCallbackResponse(
            message="Successfully authorized eBay access!",
            username=ebay_username or "eBay User",
        )

    except Exception as e:
        logger.error(f"Failed to complete eBay OAuth flow: {str(e)}")
        # Only clean up state for token exchange errors, not user info errors
        error_message = str(e).lower()
        if "token" in error_message or "authorization_code" in error_message or "invalid_grant" in error_message:
            # Token exchange failed - authorization code is invalid/expired
            await token_store.delete_request_token(state)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is invalid or expired. Please restart the authorization process.",
            ) from e
        else:
            # Other errors (user info, database, etc.) - don't clean up state, user can retry
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete authorization. Please try again.",
            ) from e


class EbayVerifyRequest(BaseModel):
    state: str
    authorization_code: str


@router.post("/verify/ebay", response_model=EbayCallbackResponse)
async def verify_ebay_oauth(
    verify_data: EbayVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> EbayCallbackResponse:
    """Complete eBay OAuth flow with authorization code (for out-of-band flow)."""
    # Retrieve the state from Redis
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
    app_result = await db.execute(select(AppConfig).where(AppConfig.provider == OAuthProvider.EBAY))
    app_config = app_result.scalar_one_or_none()

    if not app_config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="eBay OAuth is not configured.",
        )

    try:
        # Get correct URLs for this environment
        ebay_urls = get_ebay_urls(app_config)

        # Exchange authorization code for access token
        import base64

        import httpx

        # Create Basic auth header
        auth_string = f"{app_config.consumer_key}:{app_config.consumer_secret}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                ebay_urls["token_url"],
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": verify_data.authorization_code,
                    "redirect_uri": app_config.redirect_uri or "urn:ietf:wg:oauth:2.0:oob",
                },
            )
            response.raise_for_status()

            token_data_response = response.json()
            access_token = token_data_response.get("access_token")
            refresh_token = token_data_response.get("refresh_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from eBay.",
                )

            # Get user information from eBay (optional - may fail in sandbox or with limited scope)
            ebay_user_id = ""
            ebay_username = ""
            try:
                user_response = await client.get(
                    ebay_urls["user_info_url"],
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                user_response.raise_for_status()
                user_data = user_response.json()
                ebay_user_id = user_data.get("userId", "")
                ebay_username = user_data.get("username", "")
            except Exception as user_info_error:
                logger.warning(f"Could not retrieve eBay user info (continuing without it): {str(user_info_error)}")
                # Continue without user info - this is common in sandbox or with limited scopes

        # Store the access token in the database
        stmt = select(OAuthToken).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == OAuthProvider.EBAY,
        )
        token_result = await db.execute(stmt)
        existing_token = token_result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            existing_token.refresh_token = refresh_token
            existing_token.provider_user_id = ebay_user_id
            existing_token.provider_username = ebay_username
        else:
            # Create new token
            new_token = OAuthToken(
                user_id=current_user.id,
                provider=OAuthProvider.EBAY,
                access_token=access_token,
                refresh_token=refresh_token,
                provider_user_id=ebay_user_id,
                provider_username=ebay_username,
            )
            db.add(new_token)

        await db.commit()

        # Clean up temporary storage
        await token_store.delete_request_token(verify_data.state)

        return EbayCallbackResponse(
            message="Successfully authorized eBay access!",
            username=ebay_username or "eBay User",
        )

    except Exception as e:
        logger.error(f"Failed to complete eBay OAuth verification: {str(e)}")
        # Only clean up state for token exchange errors, not user info errors
        error_message = str(e).lower()
        if "token" in error_message or "authorization_code" in error_message or "invalid_grant" in error_message:
            # Token exchange failed - authorization code is invalid/expired
            await token_store.delete_request_token(verify_data.state)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is invalid or expired. Please restart the authorization process.",
            ) from e
        else:
            # Other errors (user info, database, etc.) - don't clean up state, user can retry
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete authorization. Please try again.",
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
