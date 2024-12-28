import logging
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

class LoggingCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            logger.debug(f"CORS Request: method={scope['method']}, path={scope['path']}")
            logger.debug(f"CORS Request headers: {scope['headers']}")
        
        response = await super().__call__(scope, receive, send)
        
        if scope["type"] == "http":
            logger.debug(f"CORS Response headers: {response.headers}")
        
        return response
