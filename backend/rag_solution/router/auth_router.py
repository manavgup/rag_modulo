from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx
from backend.auth.oidc import oauth
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.file_management.database import get_db
from backend.core.config import settings
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.get("/oidc-config")
async def get_oidc_config(request: Request):
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

@router.post("/token")
async def token_exchange(request: Request):
    form_data = await request.form()
    logger.info(f"Token exchange request received. Form data: {form_data}")
    
    # Create a new dictionary with the form data and add the client secret
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
        
@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.ibm.authorize_redirect(request, redirect_uri)

@router.get("/session")
async def get_session(request: Request):
    session_data = dict(request.session)
    logger.info(f"Session Data: {session_data}")
    return JSONResponse(content=session_data)

@router.get("/callback")
async def auth(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.ibm.authorize_access_token(request)
        user_info = await oauth.ibm.parse_id_token(token)

        logger.info(f"User authenticated. User info: {user_info}")
        
        user_service = UserService(db)
        db_user = user_service.get_or_create_user(
            ibm_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', 'Unknown')
        )

        logger.info(f"User in database: {db_user.__dict__}")
        
        request.session['user'] = user_info
        request.session['user_id'] = str(db_user.id)
        return RedirectResponse(url="/dashboard")
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get("/userinfo")
async def get_userinfo(request: Request):
    access_token = request.headers.get("Authorization")
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token provided")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.oidc_userinfo_endpoint}",
            headers={"Authorization": access_token}
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)

@router.get("/logout")
async def logout(request: Request):
    request.session.pop('user_id', None)
    return RedirectResponse(url="/")