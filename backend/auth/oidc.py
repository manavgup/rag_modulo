from fastapi import HTTPException, status, Request
import jwt
import logging

from authlib.integrations.starlette_client import OAuth, OAuthError
from core.config import settings

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

oauth = OAuth()

oauth.register(
    name='ibm',
    server_metadata_url=settings.oidc_discovery_endpoint,
    client_id=settings.ibm_client_id,
    client_secret=settings.ibm_client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(request: Request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    
    logger.info(f"Got User: {payload}")
    return payload

async def authorize_redirect(request: Request, redirect_uri: str):
    try:
        return await oauth.ibm.authorize_redirect(request, redirect_uri)
    except OAuthError as error:
        logger.error(f"OAuth error during authorize_redirect: {str(error)}")
        raise HTTPException(status_code=500, detail="OAuth authorization error")

async def authorize_access_token(request: Request):
    try:
        return await oauth.ibm.authorize_access_token(request)
    except OAuthError as error:
        logger.error(f"OAuth error during authorize_access_token: {str(error)}")
        raise HTTPException(status_code=500, detail="OAuth token authorization error")