import os
from typing import Optional

import redis
from loguru import logger
import signal
from redis import Redis
from redis.cluster import RedisCluster
import tickr
import json
from tickr.strategies.fibonacci.config import settings

REDIS_HOST = settings.CONNECTIONS.REDIS_HOST
REDIS_PORT = settings.CONNECTIONS.REDIS_PORT
REDIS_PASSWORD = settings.CONNECTIONS.REDIS_PASSWORD

running = True
def signal_handler(sig, frame):
    global running
    logger.warning("\nShutting down subscriber gracefully...")
    running = False


def get_redis_client() -> Optional[RedisCluster]:
    try:
        r = RedisCluster(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
            ssl=True
        )
        r.ping()
        logger.warning(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT} successfully!")
        return r
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def send_notification(client: RedisCluster, stream: str, event: str, notification: dict):
    _message = {
        "EVENT": event,
        "MESSAGE": json.dumps(notification)
    }
    if settings.DISCORD_NOTIFICATIONS is True:
        client.xadd(stream, _message, maxlen=1000)  # Keeps last 1000 messages
    else:
        logger.warning("Discord notifications off - skipping")


if __name__ == "__main__":
    RedisClient: Optional[RedisCluster] = get_redis_client()
    pubsub = RedisClient.pubsub()
    pubsub.subscribe(settings.REDIS_PRICE_STREAM_CHANNEL)  # Listen to the channel
    # Flag to control the loop
    signal.signal(signal.SIGINT, signal_handler)
    logger.info(f"Starting to listen for price stream channel: {settings.REDIS_PRICE_STREAM_CHANNEL} ...")
    try:
        while running:
            message = pubsub.get_message(timeout=1)  # Use get_message with a timeout
            if message:  # If there's a message
                if message["type"] == "message":
                    logger.success(f"Received: {message['data']}")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        pubsub.close()  # Ensure Redis PubSub connection is closed
        RedisClient.close()  # Ensure Redis client connection is closed
        logger.success("Subscriber closed.")