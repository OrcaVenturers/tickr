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


def generate_order_discord_embed(order: PendingOrder) -> dict:
    emoji = "↗" if order.orderType == "BUY" else "↘"
    embed = {
        "title": f"{emoji} `Pending` Order `({order.instrument})` Generated",
        "description": f"Please place a new {order.orderType} order",
        "color": 15844367,
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