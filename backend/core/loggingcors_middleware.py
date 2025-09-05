import logging

from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

from core.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


class LoggingCORSMiddleware(CORSMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            logger.debug(f"CORS Request: method={scope['method']}, path={scope['path']}")
            logger.debug(f"CORS Request headers: {scope['headers']}")

        await super().__call__(scope, receive, send)

        # Note: FastAPI middleware doesn't return a response object
        # The response is handled by the send callable
