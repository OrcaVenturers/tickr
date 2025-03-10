import httpx
import asyncio
from tickr.strategies.fibonacci.schemas import PendingOrder, PositionClose, PositionOpen
from tickr.strategies.fibonacci.config import settings
from tickr.strategies.RedisClient import get_redis_client
import time
import os
import json
from datetime import datetime
from loguru import logger
from table2ascii import table2ascii as t2a, PresetStyle


async def send_discord_message(embed: dict):
    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}

    if settings.DISCORD_NOTIFICATIONS:
        async with httpx.AsyncClient() as client:
            response = await client.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers)
            logger.info(response.status_code)
            return response.status_code, response.text
    else:
        return


def generate_order_discord_embed(order: PendingOrder) -> dict:
    embed = {
        "title": f"`Pending` Order `({order.instrument})` Generated",
        "description": f"Please place a new {order.orderType} pending order",
        "color": 15844367,  # Hex color (0x58C7FA -> light blue)
        "fields": [
            {"name": "**Order Type**", "value": str(order.orderType), "inline": True},
            {"name": "**Price**", "value": str(order.price), "inline": True},
            {"name": "**Fib. Ratio**", "value": str(order.fibRatioLevel), "inline": True},
            {"name": "**Generated At**", "value": order.generatedAt, "inline": False},
            {"name": "**System timestamp**", "value": order.systemTimeStamp, "inline": False},
        ],
        "footer": {
            "text": "Notified at • " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    return embed


def generate_position_closed_discord_embed(position: PositionClose) -> dict:
    embedMessageRibbon = 16711680 if position.outcome == "LOSS" else 9498256
    embed = {
        "title": f"`{position.metadata.positionType}` Position closed `({position.metadata.instrument})`: {position.outcome}",
        "description": f"An open position (level: {str(position.metadata.fibRatioLevel)}) has just been exited",
        "color": embedMessageRibbon,
        "fields": [
            {"name": "**Entry Price**", "value": str(position.metadata.positionEntryPrice), "inline": True},
            {"name": "**Entry Time**", "value": str(position.metadata.positionEntryTime), "inline": True},
            {"name": "**Take Profit**", "value": str(position.metadata.takeProfit), "inline": True},
            {"name": "**Stop Loss**", "value": str(position.metadata.stopLoss), "inline": True},
            {"name": "**Closing Price**", "value": str(position.positionClosingPrice), "inline": True},
            {"name": "**Closing Time**", "value": str(position.positionClosingTime), "inline": True},
            {"name": "**System timestamp**", "value": position.systemTimeStamp, "inline": False},
        ],
        "footer": {
            "text": "Notified at • " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    return embed


def generate_kickoff_embed(message: dict) -> dict:
    embedMessageRibbon = 12370112
    embed = {
        "title": f"`Kickoff notification` {message['INSTRUMENT']}",
        "description": f"Bot has started running with Point A: {message['POINT_A']} and Point B: {message['POINT_B']}",
        "color": embedMessageRibbon,
        "footer": {
            "text": "Notified at • " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    return embed


def format_and_notify_discord(event_type, message_content: dict):
    DISCORD_WEBHOOK_URL = settings.CONNECTIONS.DISCORD_WEBHOOK_URL
    try:
        if isinstance(message_content, str):
            message_content = json.loads(message_content)  # Convert JSON string to dict
        if event_type == "POSITION_CLOSE":
            position = PositionClose(**message_content)  # Unpack safely
            instrument = position.metadata.instrument
            embed = generate_position_closed_discord_embed(position)  # Generate embed
        elif event_type == "PENDING_ORDER":
            order = PendingOrder(**message_content)
            instrument = order.instrument
            embed = generate_order_discord_embed(order)
        elif event_type == "KICKOFF":
            instrument = message_content["INSTRUMENT"]
            webhook = DISCORD_WEBHOOK_URL.NQ if instrument.startswith("NQ") else DISCORD_WEBHOOK_URL.ES
            fib_levels: dict = message_content["FIBONACCI"]
            output = t2a(
                header=["Fibonacci Level", "Point"],
                body=[[fib, str(point)] for fib, point in fib_levels.items()],
                style=PresetStyle.thin_compact
            )
            embed = generate_kickoff_embed(message_content)
            payload = {"embeds": [embed]}
            response = httpx.post(webhook, json=payload)
            payload = {"content": f"```\n{output}\n```"}
            response = httpx.post(webhook, json=payload)
            return response.status_code, response.text
        else:
            logger.error(f"⚠️ Unknown event type: {event_type}")
            return 400, "Unknown event type"
        if embed is None:
            logger.error(f"⚠️ Failed to generate embed for event: {event_type}")
            return 500, "Embed generation failed"
        payload = {"embeds": [embed]}
        headers = {"Content-Type": "application/json"}

        webhook = DISCORD_WEBHOOK_URL.NQ if instrument.startswith("MNQ") else DISCORD_WEBHOOK_URL.ES
        response = httpx.post(webhook, json=payload, headers=headers)
        return response.status_code, response.text

    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        return 400, "Invalid JSON"

    except TypeError as e:
        logger.error(f"❌ TypeError: {e}, message_content={message_content}")
        return 400, "Invalid message structure"

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 500, str(e)


if __name__ == "__main__":
    client = get_redis_client()
    logger.info("Awaiting any notifications messages from Trading bot ...")
    while True:
        try:
            messages = client.xread({settings.DISCORD_NOTIFICATIONS_STREAM: "0"}, count=10, block=1000)
            if messages:
                for stream_name, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        event_type = msg_data.get("EVENT", "UNKNOWN_EVENT")
                        msg_content: str = msg_data.get("MESSAGE", "")
                        status_code, text = format_and_notify_discord(event_type, msg_content)
                        time.sleep(0.03) # Discord allows 50 requests per second (RPS) globally
                        if status_code == 204:
                            logger.success(f"✅ Sent notification: {msg_content}")
                            client.xdel(settings.DISCORD_NOTIFICATIONS_STREAM, msg_id)
                        else:
                            logger.error(f"❌ Failed to send notification: {status_code}, {text}")
            else:
                pass
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)