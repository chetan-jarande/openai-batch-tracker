import redis.asyncio as aioredis
from app.utils.config import REDIS_URL
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

_redis_client_instance: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """
    Returns the global Redis client instance.
    If the client is not initialized, it initializes it first.
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        logger.info("Initializing Redis client...")
        try:
            _redis_client_instance = aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            logger.info("Redis client initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize Redis client.")
            raise e
    return _redis_client_instance


async def close_redis_client():
    """
    Closes the global Redis client connection pool.
    """
    global _redis_client_instance
    if _redis_client_instance:
        logger.info("Closing Redis client connection pool...")
        try:
            await _redis_client_instance.aclose()
            _redis_client_instance = None
            logger.info("Redis client connection pool closed.")
        except Exception:
            logger.exception("Failed to close Redis client connection pool.")
