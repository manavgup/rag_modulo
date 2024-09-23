import logging
from functools import wraps

logger = logging.getLogger(__name__)

def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper

def async_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async for item in func(*args, **kwargs):
                yield item
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper
