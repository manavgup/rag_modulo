from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx
from pydantic import BaseModel
from typing import Optional
from backend.auth.oidc import oauth
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.file_management.database import get_db
from backend.core.config import settings
import uuid
import logging

logging.basicConfig(level=logging.INFO)
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

class SessionData(BaseModel):
    user: UserInfo

@router.get("/oidc-config", response_model=OIDCConfig, summary="Get OIDC Configuration",
            responses={
                200: {"description": "Successful response", "model": OIDCConfig},
                500: {"description": "Internal server error"}
            })
async def get_oidc_config(request: Request):
    """
    Retrieve the OIDC configuration for the client.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.oidc_discovery_endpoint)
        if response.status_code != 200:
            logger.error(f"Failed to fetch OIDC configuration: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch OIDC configuration")
        config = response.json()
    
    oidc_config = {
        "authority": config['issuer'],
        "client_id": settings.ibm_client_id,
        "redirect_uri": f"{settings.frontend_url}/callback",
        "response_type": "code",
        "scope": "openid profile email",
        "loadUserInfo": True,
        "metadata": {
            "issuer": config['issuer'],
            "authorization_endpoint": config['authorization_endpoint'],
            "token_endpoint": f"{settings.frontend_url}/api/auth/token",
            "userinfo_endpoint": config['userinfo_endpoint'],
            "end_session_endpoint": config.get('end_session_endpoint'),
            "jwks_uri": config['jwks_uri'],
        }
    }
    
    logger.info(f"OIDC Config Response: {oidc_config}")
    
    return JSONResponse(oidc_config)

@router.post("/token", response_model=TokenResponse, summary="Exchange Token",
             responses={
                 200: {"description": "Successful token exchange", "model": TokenResponse},
                 400: {"description": "Bad request"},
                 500: {"description": "Internal server error"}
             })
async def token_exchange(request: Request):
    """
    Exchange an authorization code for an access token.
    """
    form_data = await request.form()
    logger.info(f"Token exchange request received. Form data: {form_data}")
    
    token_request_data = dict(form_data)
    token_request_data['client_secret'] = settings.ibm_client_secret

    logger.info(f"Token request data (with client_secret): {token_request_data}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.oidc_token_url,
                data=token_request_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            logger.info(f"Token exchange response status: {response.status_code}")
            logger.info(f"Token exchange response content: {response.text}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.text}")
            return JSONResponse(content=e.response.json(), status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
@router.get("/login", summary="Initiate Login",
            responses={
                302: {"description": "Redirect to IBM OIDC authorization endpoint"},
                500: {"description": "Internal server error"}
            })
async def login(request: Request):
    """
    Initiate the login process by redirecting to the IBM OIDC authorization endpoint.
    """
    return await oauth.ibm.authorize_redirect(request, redirect_uri=f"{settings.frontend_url}/api/auth/callback")

@router.get("/session", response_model=SessionData, summary="Get Session Data",
            responses={
                200: {"description": "Successful response", "model": SessionData},
                401: {"description": "Not authenticated"},
                500: {"description": "Internal server error"}
            })
async def get_session(request: Request):
    """
    Retrieve the current session data for the authenticated user.
    """
    logger.info(f"Session request received. Session data: {dict(request.session)}")
    user = request.session.get('user')
    user_id = request.session.get('user_id')
    if user and user_id:
        logger.info(f"User found in session: {user}")
        return JSONResponse(content={"user": user, "user_id": user_id})
    logger.warning("No user found in session")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

@router.get("/callback", summary="Authentication Callback",
            responses={
                302: {"description": "Redirect to frontend dashboard"},
                500: {"description": "Authentication failed"}
            })
async def auth(request: Request, db: Session = Depends(get_db)):
    """
    Handle the authentication callback from the IBM OIDC provider.
    """
    try:
        token = await oauth.ibm.authorize_access_token(request)
        logger.info(f"Token received: {token}")

        # Extract the nonce from the token or request
        nonce = token.get('nonce') or request.query_params.get('nonce')

        user_info = await oauth.ibm.parse_id_token(token, nonce=nonce)
        logger.info(f"User authenticated. User info: {user_info}")
        
        user_service = UserService(db)
        logger.info(f"Finding or creating user: {user_info['sub']}, {user_info['email']}, {user_info.get('name', 'Unknown')}")
        db_user = user_service.get_or_create_user_by_fields(
            ibm_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', 'Unknown')
            )

        logger.info(f"User in database: {db_user.__dict__}")
        
        request.session['user'] = user_info
        request.session['user_id'] = str(db_user.id)
        logger.info(f"Session set: user_id={str(db_user.id)}")
        
        redirect_url = f"{settings.frontend_url}/?user_id={str(db_user.id)}"
        logger.info(f"Redirecting to: {redirect_url}")
        
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        return RedirectResponse(url=f"{settings.frontend_url}/signin?error=authentication_failed")

@router.get("/userinfo", response_model=UserInfo, summary="Get User Info",
            responses={
                200: {"description": "Successful response", "model": UserInfo},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"}
            })
@router.get("/userinfo", response_model=UserInfo, summary="Get User Info",
            responses={
                200: {"description": "Successful response", "model": UserInfo},
                401: {"description": "Unauthorized"},
                500: {"description": "Internal server error"}
            })
async def get_userinfo(request: Request):
    """
    Retrieve the user information from the session.
    """
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract relevant information from the session user data
    user_info = {
        "sub": user.get('sub'),
        "name": user.get('name'),
        "email": user.get('email')
    }
    
    return JSONResponse(content=user_info)

@router.get("/logout", summary="Logout User",
            responses={
                302: {"description": "Redirect to home page"},
                500: {"description": "Internal server error"}
            })
async def logout(request: Request):
    """
    Log out the current user by clearing their session.
    """
    request.session.pop('user_id', None)
    request.session.pop('user', None)
    return RedirectResponse(url="/")


@router.get("/user-id/{ibm_id}", response_model=str, summary="Get User UUID",
    responses={
        200: {"description": "Successfully retrieved user UUID", "model": str},
        404: {"description": "User not found"},
        500: {"description": "Internal server error"}
    })
async def get_user_uuid(ibm_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the UUID of a user based on their IBM identifier.

    Args:
        ibm_id (str): The IBM identifier of the user.

    Returns:
        str: The UUID of the user.

    Raises:
        HTTPException: 
            - 404 if the user is not found.
            - 500 for any internal server errors.
    """
    user_service = UserService(db)
    user = user_service.get_user_by_ibm_id(ibm_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return str(user.id)

def generate_uuid_from_string(input_string: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_OID, input_string)