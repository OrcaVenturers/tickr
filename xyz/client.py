import redis
from loguru import logger as logging

def get_redis_client():
    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True  # Ensures responses are strings instead of bytes
    )
    try:
        r.ping()
        logging.success("Connected to Redis successfully!")
        return r
    except redis.ConnectionError as e:
        logging.error(f"Failed to connect to Redis: {e}")

if __name__ == "__main__":
    get_redis_client()