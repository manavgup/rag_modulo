from fastapi import HTTPException, status, Request
import jwt
import logging

from authlib.integrations.starlette_client import OAuth, OAuthError
from core.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

oauth = OAuth()

oauth.register(
    name='ibm',
    server_metadata_url=settings.oidc_discovery_endpoint,
    client_id=settings.ibm_client_id,
    client_secret=settings.ibm_client_secret,
    client_kwargs={
        'scope': 'openid email profile',
        'token_endpoint_auth_method': 'client_secret_post'
    },
    # Add leeway for token validation
    jwks_uri=settings.oidc_discovery_endpoint + '/jwks',
    validate_iss=True,
    validate_aud=True,
    validate_exp=True,
    validate_iat=False,
    validate_nbf=True,
    leeway=50000
)

def verify_jwt_token(token: str):
    """Verify JWT token and return payload."""
    try:
        # Special handling for test token
        if token == "mock_token_for_testing":
            return {
                "sub": "test_user_id",
                "email": "test@example.com",
                "name": "Test User",
                # UUID and role will be added by middleware from headers
            }
            
        # Normal token verification
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,  # For testing environment
                "verify_exp": False,
                "verify_iat": False
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
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
        logger.debug(f"Initiating authorize_redirect with redirect_uri: {redirect_uri}")
        response = await oauth.ibm.authorize_redirect(request, redirect_uri)
        logger.debug(f"authorize_redirect response: {response}")
        return response
    except OAuthError as error:
        logger.error(f"OAuth error during authorize_redirect: {str(error)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth authorization error: {str(error)}")
    except Exception as e:
        logger.error(f"Unexpected error during authorize_redirect: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authorization error: {str(e)}")

async def authorize_access_token(request: Request):
    try:
        logger.debug("Initiating authorize_access_token")
        token = await oauth.ibm.authorize_access_token(request)
        logger.debug(f"Token received: {token}")
        return token
    except OAuthError as error:
        logger.error(f"OAuth error during authorize_access_token: {str(error)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth token authorization error: {str(error)}")
    except Exception as e:
        logger.error(f"Unexpected error during authorize_access_token: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token authorization error: {str(e)}")
