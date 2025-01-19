import functools
import logging
import re
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from core.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

open_paths = ['/api/auth/login', '/api/auth/callback', '/api/health', '/api/auth/oidc-config', '/api/auth/token', '/api/auth/userinfo']

async def authorize_dependency(request: Request):
    """
    Dependency to check if the user is authorized to access the resource.
    Uses the RBAC mapping from settings.rbac_mapping to check if the user is authorized to access the resource.

    Args:
        request (Request): The request object.

    Returns:
        bool: True if the request is authorized, raises HTTPException otherwise.
    """
    logger.info(f"AuthorizationMiddleware: Processing request to {request.url.path} by {request.state.user}")
    # print(f"AuthorizationMiddleware: Processing {request.method} request to {request.url.path} by {request.state.user}")    
    if request.url.path in open_paths:
                return True
            
    rrole = request.state.user.get('role')
    rpath = request.url.path
    try:
        if rrole:
            for pattern, method in settings.rbac_mapping[rrole].items():
                if re.match(pattern, rpath) and request.method in method:
                    return True
        raise HTTPException(status_code=403, detail=f"Failed to authorize request. {rpath} / {rrole}")

    except (KeyError, ValueError) as exc:
        logger.warning(f"Failed to authorize request. {rpath} / {rrole}")
        raise HTTPException(status_code=403, detail=f"Failed to authorize request. {rpath} / {rrole}") from exc    
    
def authorize_decorator(role: str):
    """
    Decorator to check if the user is authorized to access the resource.

    Args:
        role (str): The role required to access the resource.

    Returns:
        function: Goes to the original handler (function) if the request is authorized, raises HTTPException otherwise.
    """
    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(*args, **kwargs):
            request = kwargs['request']
            # print(f"AuthorizationDecorator: Processing {request.method} request to {request.url.path} by {request.state.user}")
            if request.url.path not in open_paths:
                if not request.state.user or request.state.user.get('role') != role:
                    logger.warning(f"AuthorizationDecorator: Unauthorized request to {request.url.path}")
                    return JSONResponse(status_code=403, content={"detail": f"User is not authorized to access this resource (requires {role} role)"})
            return await handler(*args, **kwargs)
        return wrapper
    return decorator
