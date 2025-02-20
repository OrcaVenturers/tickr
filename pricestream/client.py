import os
import redis
from loguru import logger as logging

REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # Default to "redis"
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)


def get_redis_client():
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        ssl=True
    )
    try:
        r.ping()
        logging.success(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT} successfully!")
        return r
    except redis.ConnectionError as e:
        logging.error(f"Failed to connect to Redis: {e}")

if __name__ == "__main__":
    get_redis_client()