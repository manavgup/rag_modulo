from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx
from pydantic import BaseModel
from typing import Optional

from auth.oidc import oauth
from rag_solution.services.user_service import UserService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.file_management.database import get_db
from core.config import settings
import uuid
import logging
import jwt

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
    loadUserInfo: bool
    metadata: dict

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    id_token: str

class UserInfo(BaseModel):
    sub: str
    name: Optional[str]
    email: str
    uuid: str
    role: Optional[str]

@router.get("/oidc-config", response_model=OIDCConfig)
async def get_oidc_config(request: Request):
    """
    Retrieve the OIDC configuration for the client.
    """
    logger.debug("Fetching OIDC configuration")
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.oidc_discovery_endpoint)
        if response.status_code != 200:
            logger.error(f"Failed to fetch OIDC configuration: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch OIDC configuration")
        config = response.json()

    callback_url = f"{settings.frontend_url}/api/auth/callback"
    logger.info(f"Using callback URL: {callback_url}")

    oidc_config = {
        "authority": config['issuer'],
        "client_id": settings.ibm_client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid profile email",
        "loadUserInfo": True,
        "metadata": {
            "issuer": config['issuer'],
            "authorization_endpoint": config['authorization_endpoint'],
            "token_endpoint": config['token_endpoint'],
            "userinfo_endpoint": config['userinfo_endpoint'],
            "end_session_endpoint": config.get('end_session_endpoint'),
            "jwks_uri": config['jwks_uri'],
        }
    }

    logger.info(f"OIDC Config Response: {oidc_config}")
    return JSONResponse(oidc_config)

@router.post("/token", response_model=TokenResponse)
async def token_exchange(request: Request):
    """
    Exchange an authorization code for an access token.
    """
    form_data = await request.form()
    logger.info(f"Token exchange request received. Form data: {form_data}")

    token_request_data = dict(form_data)
    token_request_data['client_secret'] = settings.ibm_client_secret

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.oidc_token_url,
                data=token_request_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            logger.info(f"Token exchange response status: {response.status_code}")
            logger.debug(f"Token exchange response content: {response.text}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            return JSONResponse(content=e.response.json(), status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/login")
async def login(request: Request):
    try:
        callback_url = f"{settings.frontend_url}/api/auth/callback"
        logger.info(f"Initiating login with redirect_uri: {callback_url}")
        return await oauth.ibm.authorize_redirect(request, callback_url)
    except Exception as e:
        logger.error(f"Error in login process: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login process")

@router.get("/callback")
async def auth(request: Request, db: Session = Depends(get_db)):
    try:
        logger.info("Received authentication callback")
        token = await oauth.ibm.authorize_access_token(request)
        logger.info("Successfully obtained access token")
        logger.debug(f"Token content: {token}")

        user = token.get('userinfo')
        if not user:
            logger.error("User info not found in token")
            raise HTTPException(status_code=400, detail="User info not found in token")

        logger.info(f"Authenticated user: {user.get('email')}")

        # Create or get user
        user_service = UserService(db)
        db_user = user_service.get_or_create_user_by_fields(
            ibm_id=user['sub'],
            email=user['email'],
            name=user.get('name', 'Unknown')
        )
        logger.info(f"User in database: {db_user.id}")

        # Initialize default templates for user
        try:
            # Get user's provider
            provider_service = LLMProviderService(db)
            provider = provider_service.get_user_provider(db_user.id)
            if not provider:
                logger.error("No LLM provider available for user")
                raise HTTPException(status_code=500, detail="No LLM provider available")

            # Initialize templates
            template_service = PromptTemplateService(db)
            template_service.initialize_default_templates(db_user.id, provider.name)
            logger.info("Successfully initialized default templates for user")
        except Exception as e:
            logger.error(f"Error initializing templates: {str(e)}")
            # Continue with authentication even if template initialization fails
            # The templates will be created on demand when needed

        jwt_token = token.get('id_token')
        if not jwt_token:
            logger.error("No JWT token received from OAuth provider")
            raise HTTPException(status_code=400, detail="No JWT token received from OAuth provider")

        custom_jwt_payload = {
            "sub": user['sub'],
            "email": user['email'],
            "name": user.get('name', 'Unknown'),
            "uuid": str(db_user.id),
            "exp": token.get('expires_at'),
            "role": db_user.role
        }
        custom_jwt = jwt.encode(custom_jwt_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        redirect_url = f"{settings.frontend_url}{settings.frontend_callback}?token={custom_jwt}"
        logger.info(f"Redirecting to frontend: {redirect_url}")

        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Error in authentication callback: {str(e)}", exc_info=True)
        error_redirect = f"{settings.frontend_url}/signin?error=authentication_failed"
        return RedirectResponse(url=error_redirect)

@router.post("/logout")
async def logout(request: Request):
    """
    Log out the current user.
    """
    logger.info("Logging out user")
    request.session.clear()
    return JSONResponse(content={"message": "Logged out successfully"})

@router.get("/userinfo", response_model=UserInfo)
async def get_userinfo(request: Request):
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
        if scheme.lower() != 'bearer':
            logger.warning(f"Invalid authorization scheme: {scheme}")
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        
        logger.info("Decoding JWT token")
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        logger.info(f"JWT payload: {payload}")
        
        user_info = UserInfo(
            sub=payload.get('sub'),
            name=payload.get('name'),
            email=payload.get('email'),
            uuid=payload.get('uuid'),
            role=payload.get('role', 'user')
        )
        logger.info(f"Retrieved user info for user: {user_info.email}")
        return JSONResponse(content=user_info.model_dump())
    except jwt.PyJWTError as e:
        logger.error(f"Error decoding JWT: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/check-auth")
async def check_auth(request: Request):
    """
    Check if the user is authenticated.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        logger.info("No Authorization header found")
        return JSONResponse(content={"authenticated": False})

    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            logger.warning(f"Invalid authorization scheme: {scheme}")
            return JSONResponse(content={"authenticated": False})

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get('sub')
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
        logger.warning(f"Invalid JWT token: {str(e)}")
        return JSONResponse(content={"authenticated": False, "error": "Invalid token"})

@router.get("/session")
async def session_status(request: Request):
    """
    Check session status and retrieve user info if authenticated.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        logger.info("No Authorization header found")
        return JSONResponse(content={"authenticated": False, "user": None})

    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            logger.warning(f"Invalid authorization scheme: {scheme}")
            return JSONResponse(content={"authenticated": False, "user": None})

        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_info = UserInfo(
            sub=payload.get('sub'),
            name=payload.get('name'),
            email=payload.get('email'),
            uuid=payload.get('uuid'),
            role=payload.get('role', 'user')
        )
        logger.info(f"User is authenticated: {user_info.email}")
        return JSONResponse(content={"authenticated": True, "user": user_info.model_dump()})
    except jwt.PyJWTError as e:
        logger.error(f"Error decoding JWT: {str(e)}")
        return JSONResponse(content={"authenticated": False, "error": "Invalid token"})
