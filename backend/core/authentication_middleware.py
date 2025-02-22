import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from core.config import settings
from auth.oidc import verify_jwt_token
from sqlalchemy.orm import Session
from rag_solution.file_management.database import get_db
from rag_solution.services.user_service import UserService

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"AuthMiddleware: Processing request to {request.url.path}")
        logger.debug(f"AuthMiddleware: Request headers: {request.headers}")

        # Check for JWT in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            logger.info("AuthMiddleware: JWT token found in Authorization header")
            token = auth_header.split(' ')[1]
            try:
                # Verify JWT using the verify_jwt_token function from oidc.py
                payload = verify_jwt_token(token)
                request.state.user = {
                    'id': payload.get('sub'),
                    'email': payload.get('email'),
                    'name': payload.get('name'),
                    'uuid': payload.get('uuid'),  # Extract UUID from payload
                    'role': payload.get('role')
                }
                logger.info(f"AuthMiddleware: JWT token validated successfully. User: {request.state.user}")
            except jwt.ExpiredSignatureError:
                logger.warning("AuthMiddleware: Expired JWT token")
                return JSONResponse(status_code=401, content={"detail": "Token has expired"})
            except jwt.InvalidTokenError as e:
                logger.warning(f"AuthMiddleware: Invalid JWT token - {str(e)}")
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})
        else:
            logger.info("AuthMiddleware: No JWT token found")

        open_paths = [
            '/api/',
            '/api/auth/login',
            '/api/auth/callback',
            '/api/health',
            '/api/auth/oidc-config',
            '/api/auth/token',
            '/api/docs',
            '/api/openapi.json',
            '/api/redoc',
            '/api/docs/oauth2-redirect',
            '/api/docs/swagger-ui.css',
            '/api/docs/swagger-ui-bundle.js',
            '/api/docs/swagger-ui-standalone-preset.js',
            '/api/docs/favicon.png'
        ]

        # Skip authentication for open paths and static files
        if request.url.path in open_paths or request.url.path.startswith('/static/'):
            logger.info(f"AuthMiddleware: Allowing access to open path: {request.url.path}")
            return await call_next(request)

        # Require authentication for all other paths
        if not hasattr(request.state, 'user'):
            logger.warning(f"AuthMiddleware: User not authenticated for protected endpoint: {request.url.path}")
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        logger.info("AuthMiddleware: Passing request to next middleware/handler")
        response = await call_next(request)
        logger.info(f"AuthMiddleware: Response status code: {response.status_code}")
        
        return response
