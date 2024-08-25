from fastapi import HTTPException, status, Request
from authlib.integrations.starlette_client import OAuth
from backend.core.config import settings
import logging

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

# oauth2_scheme = OAuth2AuthorizationCodeBearer(
#     authorizationUrl=settings.oidc_auth_url,
#     tokenUrl=settings.oidc_token_url,
# )

async def get_current_user(request: Request):
    user = request.session.get('user')

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info(f"Got User: {user}")
    return user