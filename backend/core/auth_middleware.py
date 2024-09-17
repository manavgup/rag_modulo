import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.services.user_service import UserService
import jwt
from backend.core.config import settings

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"AuthMiddleware: Processing request to {request.url.path}")
        logger.debug(f"AuthMiddleware: Request headers: {request.headers}")
        logger.debug(f"AuthMiddleware: Request scope keys: {request.scope.keys()}")

        # Check for JWT in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            logger.info("AuthMiddleware: JWT token found in Authorization header")
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
                request.state.user_id = payload.get('uuid')
                logger.info(f"AuthMiddleware: User authenticated from JWT, user_id: {request.state.user_id}")
            except jwt.ExpiredSignatureError:
                logger.warning("AuthMiddleware: Expired JWT token")
                return JSONResponse(status_code=401, content={"detail": "Token has expired"})
            except jwt.InvalidTokenError as e:
                logger.warning(f"AuthMiddleware: Invalid JWT token - {str(e)}")
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})
        # Fallback to session-based auth if JWT is not present
        elif 'session' in request.scope:
            logger.info("AuthMiddleware: Session found in request scope")
            try:
                session = request.session
                logger.debug(f"AuthMiddleware: Session accessed successfully: {session}")
                user_id = session.get('user_id')
                if user_id:
                    request.state.user_id = user_id
                    logger.info(f"AuthMiddleware: User authenticated from session, user_id: {user_id}")
                else:
                    logger.info("AuthMiddleware: No user_id in session, attempting to get or create user")
                    # If user_id is not in session, try to get or create user
                    user_info = session.get('user')
                    if user_info:
                        logger.debug(f"AuthMiddleware: User info found in session: {user_info}")
                        db_generator = get_db()
                        db = next(db_generator)
                        try:
                            user_service = UserService(db)
                            db_user = user_service.get_or_create_user_by_fields(
                                ibm_id=user_info.get('sub'),
                                email=user_info.get('email'),
                                name=user_info.get('name', 'Unknown')
                            )
                            request.state.user_id = str(db_user.id)
                            session['user_id'] = str(db_user.id)
                            logger.info(f"AuthMiddleware: User created/retrieved in database: {db_user.id}")
                        except Exception as e:
                            logger.error(f"AuthMiddleware: Error creating/retrieving user: {str(e)}")
                            return JSONResponse(status_code=500, content={"detail": "Internal server error: Unable to create/retrieve user"})
                        finally:
                            try:
                                next(db_generator)  # This will trigger the finally block in get_db()
                            except StopIteration:
                                pass  # This is expected
                    else:
                        logger.warning("AuthMiddleware: No user info found in session")
            except Exception as e:
                logger.error(f"AuthMiddleware: Error accessing session: {str(e)}")
                return JSONResponse(status_code=500, content={"detail": "Internal server error: Unable to access session"})
        else:
            logger.warning("AuthMiddleware: No JWT or session found")

        open_paths = ['/api/auth/login', '/api/auth/callback', '/api/health', '/api/auth/session', '/api/auth/oidc-config', '/api/auth/token']

        if request.url.path.startswith("/api/") and request.url.path not in open_paths:
            if not hasattr(request.state, 'user_id'):
                logger.warning(f"AuthMiddleware: User not authenticated for protected endpoint: {request.url.path}")
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        logger.info("AuthMiddleware: Passing request to next middleware/handler")
        response = await call_next(request)
        logger.info(f"AuthMiddleware: Response status code: {response.status_code}")
        return response