import logging
from datetime import datetime, timedelta
from typing import Annotated, Any

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.oidc import create_access_token, oauth
from core.config import Settings, get_settings
from rag_solution.core.device_flow import (
    DeviceFlowConfig,
    DeviceFlowRecord,
    generate_user_code,
    get_device_flow_storage,
    parse_device_flow_error,
)
from rag_solution.file_management.database import get_db
from rag_solution.services.user_service import UserService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Define response models
class OIDCConfig(BaseModel):
    authority: str
    client_id: str
    redirect_uri: str
    response_type: str
    scope: str
    load_user_info: bool
    metadata: dict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    id_token: str


class UserInfo(BaseModel):
    sub: str
    name: str | None
    email: str
    uuid: str
    role: str | None


@router.get("/oidc-config", response_model=OIDCConfig)
async def get_oidc_config(settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """
    Retrieve the OIDC configuration for the client.
    """
    logger.debug("Fetching OIDC configuration")
    if not settings.oidc_discovery_endpoint:
        raise HTTPException(status_code=500, detail="OIDC discovery endpoint not configured")
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.oidc_discovery_endpoint)
        if response.status_code != 200:
            logger.error(f"Failed to fetch OIDC configuration: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch OIDC configuration")
        config = response.json()

    callback_url = f"{settings.frontend_url}/api/auth/callback"
    logger.info(f"Using callback URL: {callback_url}")

    oidc_config = {
        "authority": config["issuer"],
        "client_id": settings.ibm_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid profile email",
        "loadUserInfo": True,
        "metadata": {
            "issuer": config["issuer"],
            "authorization_endpoint": config["authorization_endpoint"],
            "token_endpoint": config["token_endpoint"],
            "userinfo_endpoint": config["userinfo_endpoint"],
            "end_session_endpoint": config.get("end_session_endpoint"),
            "jwks_uri": config["jwks_uri"],
        },
    }

    logger.info(f"OIDC Config Response: {oidc_config}")
    return JSONResponse(oidc_config)


@router.post("/token", response_model=TokenResponse)
async def token_exchange(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """
    Exchange an authorization code for an access token.
    """
    form_data = await request.form()
    logger.info(f"Token exchange request received. Form data: {form_data}")

    token_request_data = dict(form_data)
    if settings.ibm_client_secret:
        token_request_data["client_secret"] = settings.ibm_client_secret

    if not settings.oidc_token_url:
        raise HTTPException(status_code=500, detail="OIDC token URL not configured")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.oidc_token_url,
                data=token_request_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            logger.info(f"Token exchange response status: {response.status_code}")
            logger.debug(f"Token exchange response content: {response.text}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            return JSONResponse(content=e.response.json(), status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/login")
async def login(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> Response:
    try:
        callback_url = f"{settings.frontend_url}/api/auth/callback"
        logger.info(f"Initiating login with redirect_uri: {callback_url}")
        result = await oauth.ibm.authorize_redirect(request, callback_url)
        # The OAuth library returns Any, so we need to cast it to Response
        return result  # type: ignore
    except Exception as e:
        logger.error(f"Error in login process: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login process") from e


@router.get("/callback")
async def auth(request: Request, db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]) -> Response:
    try:
        logger.info("Received authentication callback")
        token = await oauth.ibm.authorize_access_token(request)
        logger.info("Successfully obtained access token")
        logger.debug(f"Token content: {token}")

        user = token.get("userinfo")
        if not user:
            logger.error("User info not found in token")
            raise HTTPException(status_code=400, detail="User info not found in token")

        logger.info(f"Authenticated user: {user.get('email')}")

        # Create or get user
        user_service = UserService(db, settings)
        db_user = user_service.get_or_create_user_by_fields(ibm_id=user["sub"], email=user["email"], name=user.get("name", "Unknown"))
        logger.info(f"User in database: {db_user.id}")

        jwt_token = token.get("id_token")
        if not jwt_token:
            logger.error("No JWT token received from OAuth provider")
            raise HTTPException(status_code=400, detail="No JWT token received from OAuth provider")

        custom_jwt_payload = {
            "sub": user["sub"],
            "email": user["email"],
            "name": user.get("name", "Unknown"),
            "uuid": str(db_user.id),
            "exp": token.get("expires_at"),
            "role": db_user.role,
        }
        custom_jwt = jwt.encode(custom_jwt_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        # PyJWT always returns a string in modern versions, but ensure it's a string
        custom_jwt_str = custom_jwt.decode("utf-8") if isinstance(custom_jwt, bytes) else str(custom_jwt)

        redirect_url = f"{settings.frontend_url}{settings.frontend_callback}?token={custom_jwt_str}"
        logger.info(f"Redirecting to frontend: {redirect_url}")

        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Error in authentication callback: {e!s}", exc_info=True)
        error_redirect = f"{settings.frontend_url}/signin?error=authentication_failed"
        return RedirectResponse(url=error_redirect)


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    """
    Log out the current user.
    """
    logger.info("Logging out user")
    request.session.clear()
    return JSONResponse(content={"message": "Logged out successfully"})


@router.get("/userinfo", response_model=UserInfo)
async def get_userinfo(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """
    Retrieve the user information from the JWT Token.
    """
    logger.info("Received request for /userinfo")
    authorization = request.headers.get("Authorization")
    if not authorization:
        logger.warning("No Authorization header found")
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid authorization scheme: {scheme}")
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")

        logger.info("Decoding JWT token")
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        logger.info(f"JWT payload: {payload}")

        user_info = UserInfo(
            sub=payload.get("sub"),
            name=payload.get("name"),
            email=payload.get("email"),
            uuid=payload.get("uuid"),
            role=payload.get("role", "user"),
        )
        logger.info(f"Retrieved user info for user: {user_info.email}")
        return JSONResponse(content=user_info.model_dump())
    except jwt.PyJWTError as e:
        logger.error(f"Error decoding JWT: {e!s}")
        raise HTTPException(status_code=401, detail="Invalid token") from e


@router.get("/check-auth")
async def check_auth(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """
    Check if the user is authenticated.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        logger.info("No Authorization header found")
        return JSONResponse(content={"authenticated": False})

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid authorization scheme: {scheme}")
            return JSONResponse(content={"authenticated": False})

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id:
            logger.info(f"User is authenticated: {user_id}")
            return JSONResponse(content={"authenticated": True, "user_id": user_id})
        else:
            logger.warning("Invalid JWT token: no sub claim")
            return JSONResponse(content={"authenticated": False, "error": "Invalid token"})
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return JSONResponse(content={"authenticated": False, "error": "Token expired"})
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e!s}")
        return JSONResponse(content={"authenticated": False, "error": "Invalid token"})


@router.get("/session")
async def session_status(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """
    Check session status and retrieve user info if authenticated.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        logger.info("No Authorization header found")
        return JSONResponse(content={"authenticated": False, "user": None})

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid authorization scheme: {scheme}")
            return JSONResponse(content={"authenticated": False, "user": None})

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_info = UserInfo(
            sub=payload.get("sub"),
            name=payload.get("name"),
            email=payload.get("email"),
            uuid=payload.get("uuid"),
            role=payload.get("role", "user"),
        )
        logger.info(f"User is authenticated: {user_info.email}")
        return JSONResponse(content={"authenticated": True, "user": user_info.model_dump()})
    except jwt.PyJWTError as e:
        logger.error(f"Error decoding JWT: {e!s}")
        return JSONResponse(content={"authenticated": False, "error": "Invalid token"})


# Device Flow Models
class DeviceFlowStartRequest(BaseModel):
    """Request to start device flow authorization."""

    provider: str = "ibm"  # Currently only IBM is supported


class DeviceFlowStartResponse(BaseModel):
    """Response for device flow authorization start."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None = None
    expires_in: int
    interval: int


class DeviceFlowPollRequest(BaseModel):
    """Request to poll for device flow token."""

    device_code: str


class DeviceFlowPollResponse(BaseModel):
    """Response for device flow token polling."""

    status: str  # "pending", "success", "error"
    access_token: str | None = None
    user: dict[str, Any] | None = None
    error: str | None = None
    error_description: str | None = None


# CLI Browser-based Authentication Endpoints
class CLIAuthRequest(BaseModel):
    """Request to start CLI browser-based authentication."""

    provider: str = "ibm"
    callback_port: int | None = None  # CLI will provide callback port


class CLIAuthResponse(BaseModel):
    """Response for CLI authentication initiation."""

    auth_url: str
    state: str


@router.post("/cli/start", response_model=CLIAuthResponse)
async def start_cli_auth(request: CLIAuthRequest, settings: Annotated[Settings, Depends(get_settings)]) -> CLIAuthResponse:
    """
    Start CLI browser-based authentication.

    This endpoint creates an authentication URL that the CLI can open
    in the user's browser, with a callback to the CLI's local server.
    """
    if request.provider != "ibm":
        raise HTTPException(status_code=400, detail="Only IBM provider is currently supported")

    # Generate a unique state parameter for security
    import secrets

    state = secrets.token_urlsafe(32)

    # Store the state and callback port for validation
    # In production, use Redis or database storage
    storage = get_device_flow_storage()
    record = DeviceFlowRecord(
        device_code=state,  # Reuse device_code field for state
        user_code="CLI",  # Mark as CLI authentication
        verification_uri="",
        expires_at=datetime.now() + timedelta(minutes=10),
        interval=0,
        status="pending",
    )
    storage.store_record(record)

    # Build the authentication URL with CLI callback
    callback_port = request.callback_port or 8080
    callback_uri = f"http://localhost:{callback_port}/callback"

    auth_url = f"http://localhost:8000/api/auth/login?" f"redirect_uri={callback_uri}&" f"state={state}"

    return CLIAuthResponse(auth_url=auth_url, state=state)


class CLITokenRequest(BaseModel):
    """Request to exchange authorization code for JWT token."""

    code: str
    state: str


class CLITokenResponse(BaseModel):
    """Response with JWT token for CLI."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict[str, Any]


@router.post("/cli/token", response_model=CLITokenResponse)
async def exchange_cli_token(request: CLITokenRequest, settings: Annotated[Settings, Depends(get_settings)], db: Session = Depends(get_db)) -> CLITokenResponse:
    """
    Exchange authorization code for JWT token in CLI authentication flow.

    This endpoint is called by the CLI after the user completes authentication
    in their browser and the callback is received.
    """
    # Validate the state parameter
    storage = get_device_flow_storage()
    record = storage.get_record(request.state)

    if not record or record.user_code != "CLI":
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")

    if record.is_expired():
        raise HTTPException(status_code=400, detail="Authentication session expired")

    # For testing: return success with mock data (to test the flow)
    # In production, this would exchange code with IBM OIDC
    user_email = "test@ibm.com"

    # Create or update user in database using existing service
    user_service = UserService(db)
    user = user_service.get_or_create_user_by_fields(username=user_email, email=user_email)

    # Create JWT token for our application
    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email, "username": user.username, "uuid": str(user.id), "role": "user"})

    # Mark the CLI authentication as completed
    record.status = "completed"
    record.user_id = str(user.id)
    storage.update_record(record)

    return CLITokenResponse(
        access_token=jwt_token,
        expires_in=86400,  # 24 hours
        user={"id": user.id, "email": user.email, "username": user.username},
    )


# Device Flow Endpoints (kept for future use with other providers)
@router.post("/device/start", response_model=DeviceFlowStartResponse)
async def start_device_flow(request: DeviceFlowStartRequest, settings: Annotated[Settings, Depends(get_settings)]) -> DeviceFlowStartResponse:
    """
    Start OAuth 2.0 Device Authorization Flow.

    This endpoint initiates the device flow by requesting a device code
    and user code from the IBM OIDC provider.
    """
    if request.provider != "ibm":
        raise HTTPException(status_code=400, detail="Only IBM provider is currently supported")

    # Create device flow configuration from settings
    config = DeviceFlowConfig(
        client_id=settings.ibm_client_id,
        client_secret=settings.ibm_client_secret,
        device_auth_url=getattr(settings, "oidc_device_auth_url", "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/device_authorization"),
        token_url=getattr(settings, "oidc_token_url", "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token"),
    )

    # Request device authorization from IBM OIDC
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                str(config.device_auth_url), data={"client_id": config.client_id, "scope": "openid email profile"}, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Device flow start failed: {error_data}")
                raise HTTPException(status_code=response.status_code, detail=error_data.get("error_description", "Device flow authorization failed"))

            data = response.json()

            # Store device flow record for polling
            storage = get_device_flow_storage()
            record = DeviceFlowRecord(
                device_code=data["device_code"],
                user_code=data.get("user_code", generate_user_code()),
                verification_uri=data["verification_uri"],
                verification_uri_complete=data.get("verification_uri_complete"),
                expires_at=datetime.now() + timedelta(seconds=data.get("expires_in", 600)),
                interval=data.get("interval", 5),
                status="pending",
            )
            storage.store_record(record)

            return DeviceFlowStartResponse(
                device_code=data["device_code"],
                user_code=data.get("user_code", record.user_code),
                verification_uri=data["verification_uri"],
                verification_uri_complete=data.get("verification_uri_complete"),
                expires_in=data.get("expires_in", 600),
                interval=data.get("interval", 5),
            )

        except httpx.RequestError as e:
            logger.error(f"Network error during device flow start: {e}")
            raise HTTPException(status_code=503, detail="Failed to contact authorization server") from e


@router.post("/device/poll", response_model=DeviceFlowPollResponse)
async def poll_device_token(request: DeviceFlowPollRequest, settings: Annotated[Settings, Depends(get_settings)], db: Session = Depends(get_db)) -> DeviceFlowPollResponse:
    """
    Poll for device flow token.

    This endpoint polls the IBM OIDC provider to check if the user
    has completed the authorization process.
    """
    storage = get_device_flow_storage()
    record = storage.get_record(request.device_code)

    if not record:
        return DeviceFlowPollResponse(status="error", error="invalid_grant", error_description="Device code not found or expired")

    if record.is_expired():
        return DeviceFlowPollResponse(status="error", error="expired_token", error_description="Device code has expired")

    # Create device flow configuration
    config = DeviceFlowConfig(
        client_id=settings.ibm_client_id,
        client_secret=settings.ibm_client_secret,
        device_auth_url=getattr(settings, "oidc_device_auth_url", "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/device_authorization"),
        token_url=getattr(settings, "oidc_token_url", "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token"),
    )

    # Poll IBM OIDC token endpoint
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                str(config.token_url),
                data={"grant_type": "urn:ietf:params:oauth:grant-type:device_code", "device_code": request.device_code, "client_id": config.client_id, "client_secret": config.client_secret},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                # Success! User has authorized
                data = response.json()

                # Extract user info from token or userinfo endpoint
                user_info = data.get("userinfo", {})
                if not user_info and "access_token" in data:
                    # Try to decode the access token or fetch userinfo
                    user_info = {"sub": data.get("sub", "unknown"), "email": data.get("email", "unknown@ibm.com")}

                # Create or update user in database
                user_service = UserService(db)
                user = user_service.get_or_create_user_by_fields(username=user_info.get("email", "unknown"), email=user_info.get("email", "unknown@ibm.com"))

                # Create JWT token for our application
                jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email, "username": user.username, "uuid": str(user.id), "role": "user"})

                # Update device flow record status
                record.status = "authorized"
                record.user_id = str(user.id)
                storage.update_record(record)

                return DeviceFlowPollResponse(status="success", access_token=jwt_token, user={"id": user.id, "email": user.email, "username": user.username})

            elif response.status_code == 400:
                # Check for specific error codes
                error_data = response.json()
                error_code = error_data.get("error", "unknown_error")

                error_info = parse_device_flow_error(error_code)

                if error_info["retry"]:
                    # Still pending or need to slow down
                    return DeviceFlowPollResponse(status="pending", error=error_code, error_description=error_info["message"])
                else:
                    # Terminal error
                    record.status = "denied" if error_code == "access_denied" else "expired"
                    storage.update_record(record)

                    return DeviceFlowPollResponse(status="error", error=error_code, error_description=error_info["message"])

            else:
                # Unexpected response
                logger.error(f"Unexpected response from token endpoint: {response.status_code}")
                return DeviceFlowPollResponse(status="error", error="server_error", error_description="Unexpected response from authorization server")

        except httpx.RequestError as e:
            logger.error(f"Network error during device flow polling: {e}")
            return DeviceFlowPollResponse(status="error", error="network_error", error_description="Failed to contact authorization server")
