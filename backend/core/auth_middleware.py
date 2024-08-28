import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.file_management.database import get_db
from uuid import UUID

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.debug(f"AuthMiddleware: Processing request to {request.url.path}")

        # List of paths that don't require authentication
        open_paths = ['/api/auth/login', '/api/auth/callback', '/api/health', '/api/auth/session', '/api/auth/oidc-config']

        if request.url.path.startswith("/api/"):
            logger.debug("AuthMiddleware: Request is to an API endpoint")

            # Ensure session exists
            if 'session' not in request.scope:
                request.scope['session'] = {}
                logger.debug("AuthMiddleware: Created new session")

            session = request.scope['session']

            # Check if the path requires authentication
            if request.url.path not in open_paths:
                user_id = session.get('user_id')
                if not user_id:
                    logger.debug("AuthMiddleware: User not authenticated for protected endpoint")
                    return JSONResponse(status_code=401, content={"detail": "Authentication required"})

                logger.debug(f"AuthMiddleware: User authenticated, user_id: {user_id}")

                # Verify the user exists in the database
                db = next(get_db())
                user_service = UserService(db)
                try:
                    # Ensure user_id is a valid UUID
                    try:
                        uuid_user_id = UUID(user_id)
                    except ValueError:
                        logger.warning(f"AuthMiddleware: Invalid UUID format for user_id: {user_id}")
                        return JSONResponse(status_code=401, content={"detail": "Invalid user ID format"})

                    user = user_service.get_user_by_id(str(uuid_user_id))
                    if not user:
                        logger.warning(f"AuthMiddleware: User not found for user_id: {user_id}")
                        return JSONResponse(status_code=401, content={"detail": "User not found"})

                    # Add user to request state for easier access in route handlers
                    request.state.user = user
                    logger.debug(f"AuthMiddleware: User {user.id} verified and added to request state")

                except Exception as e:
                    logger.error(f"AuthMiddleware: Error verifying user: {str(e)}", exc_info=True)
                    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
                finally:
                    db.close()
            else:
                logger.debug(f"AuthMiddleware: Allowing unauthenticated access to {request.url.path}")

        logger.debug("AuthMiddleware: Passing request to next middleware/handler")
        response = await call_next(request)
        return response