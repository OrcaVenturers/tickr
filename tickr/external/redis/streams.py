from loguru import logger
from redis.cluster import RedisCluster
import json

from tickr.core.schemas import PendingOrder, PendingOrderPlacement
from tickr.strategies.fibonacci.config import settings
from typing import Optional
from tickr.external.redis.client import get_redis_client
from datetime import datetime


def add_message_to_stream(client: RedisCluster, stream: str, event: str, message: dict):
    _message = {
        "EVENT": event,
        "MESSAGE": json.dumps(message)
    }
    if settings.DISCORD_NOTIFICATIONS is True:
        client.xadd(stream, _message, maxlen=1000)
    else:
        logger.warning("Discord notifications off - skipping")


def get_messages_from_stream(client: RedisCluster, stream: str):
    _messages = client.xread({stream: "0"}, count=40, block=1000)
    return _messages



if __name__ == "__main__":
    RedisClient: Optional[RedisCluster] = get_redis_client()
    try:
        pendingOrderGenerated = PendingOrder(
            instrument=settings.INSTRUMENT,
            orderType="FLAT",
            price=20450,
            fibRatioLevel=1.0,
            takeProfit=21500,
            stopLoss=21070,
            generatedAt=str(datetime.now()),
            systemTimeStamp=str(datetime.now()),
        )
        pendingOrderPlacementMessage = PendingOrderPlacement(
            metadata = pendingOrderGenerated,
            Instrument = settings.INSTRUMENT,
            AtmStrategy = f"4_10",
            Quantity=3
        )
        logger.info(f"Adding message to stream: {pendingOrderPlacementMessage.model_dump()}")
        add_message_to_stream(
            RedisClient,
            stream=settings.ORDERS_NOTIFICATIONS_STREAM,
            event="PENDING_ORDER",
            message=pendingOrderPlacementMessage.model_dump()
        )

        # logger.info(f"Getting messages from stream: {settings.ORDERS_NOTIFICATIONS_STREAM}")
        # messages = get_messages_from_stream(RedisClient, stream=settings.ORDERS_NOTIFICATIONS_STREAM)
        # print(messages)

    except Exception as e:
        logger.error(f"Error occurred: {e}")
    finally:
        RedisClient.close()
        logger.success("Subscriber closed.")