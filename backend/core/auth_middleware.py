import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from backend.rag_solution.file_management.database import get_db
from backend.rag_solution.services.user_service import UserService

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug(f"AuthMiddleware: Processing request to {request.url.path}")
        logger.debug(f"AuthMiddleware: Request headers: {request.headers}")
        logger.debug(f"AuthMiddleware: Request scope keys: {request.scope.keys()}")

        # Check for X-User-UUID header
        user_uuid = request.headers.get('X-User-UUID')
        if user_uuid:
            logger.debug(f"AuthMiddleware: X-User-UUID header found: {user_uuid}")
            request.state.user_id = user_uuid
        elif 'session' in request.scope:
            logger.debug("AuthMiddleware: Session found in request scope")
            try:
                session = request.session
                logger.debug(f"AuthMiddleware: Session accessed successfully: {session}")
                user_id = session.get('user_id')
                if user_id:
                    request.state.user_id = user_id
                    logger.debug(f"AuthMiddleware: User authenticated from session, user_id: {user_id}")
                else:
                    # If user_id is not in session, try to get or create user
                    user_info = session.get('user')
                    if user_info:
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
                            logger.info(f"User created/retrieved in database: {db_user.id}")
                        except Exception as e:
                            logger.error(f"Error creating/retrieving user: {str(e)}")
                        finally:
                            try:
                                next(db_generator)  # This will trigger the finally block in get_db()
                            except StopIteration:
                                pass  # This is expected
            except Exception as e:
                logger.error(f"AuthMiddleware: Error accessing session: {str(e)}")
                return JSONResponse(status_code=500, content={"detail": "Internal server error: Unable to access session"})
        else:
            logger.warning("AuthMiddleware: No session or X-User-UUID header found")

        open_paths = ['/api/auth/login', '/api/auth/callback', '/api/health', '/api/auth/session', '/api/auth/oidc-config']

        if request.url.path.startswith("/api/") and request.url.path not in open_paths:
            if not hasattr(request.state, 'user_id'):
                logger.warning("AuthMiddleware: User not authenticated for protected endpoint")
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        logger.debug("AuthMiddleware: Passing request to next middleware/handler")
        response = await call_next(request)
        logger.debug(f"AuthMiddleware: Response status code: {response.status_code}")
        return response