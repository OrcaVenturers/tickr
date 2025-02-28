from datetime import time, datetime
from enum import Enum

DISCORD_NOTIFICATIONS: bool = False
REDIS_NOTIFICATIONS_STREAM: str = "DISCORD_NOTIFICATIONS_STREAM"
REDIS_PRICE_STREAM_CHANNEL: str = "NT8_NQ_PRICESTREAM"

FIBONACCI_RATIOS = [
        0 ,0.23, 0.38, 0.50, 0.618, 0.78, 1.0, 1.23, 1.618, 2.14, 2.618, 3.618,
        -0.23, -0.618, -1.14, -1.618, -2.14, -2.618, -3.618
    ]

class CandlestickComputationTime(Enum):
    start: time = time(14, 30)
    end: time = time(15, 00)


class CandlestickKickoffPoints(Enum):
    """Overrides the kickoff points for the bot"""
    POINT_A: float = None
    POINT_B: float = None


class TradeExecutionSettings(Enum):
    """Overrides the kickoff points for the bot"""
    takeProfit: float = 20.0
    stopLoss: float = 20.0
    reactivationDistance: float = None


#TODO: Implement this?
class RegularTradeExecutionSettings(Enum):
    """Overrides the kickoff points for the bot"""
    takeProfit: float = 20.0
    stopLoss: float = 20.0
    reactivationDistance: float = None

#TODO: Implement this?
class OvernightTradeExecutionSettings(Enum): # 23.10 to 13.15
    """Overrides the kickoff points for the bot"""
    takeProfit: float = 20.0
    stopLoss: float = 20.0
    reactivationDistance: float = None

'''
Allowable Start and End times for the PendingOrder AND Positions Entry/Exit
Other parts of the bot like Activation/Reactivation and candlestick computation works all the time
'''
ALLOWED_TIMES = [
    (time(15, 5), time(15, 57)),
    (time(16, 3), time(16, 57)),
    (time(17, 3), time(17, 57)),
    (time(18, 3), time(18, 57)),
    (time(19, 3), time(19, 57)),
    (time(20, 3), time(20, 45)), # Restriction: MOC closing window

    (time(23, 10), time(23, 57)),
    (time(0, 3), time(0, 57)),
    (time(1, 3), time(1, 57)),
    (time(2, 3), time(2, 57)),
    (time(3, 3), time(3, 57)),
    (time(4, 3), time(4, 57)),
    (time(5, 3), time(5, 57)),
    (time(6, 3), time(6, 57)),
    (time(7, 3), time(7, 57)),
    (time(8, 3), time(8, 57)),
    (time(9, 3), time(9, 57)),
    (time(10, 3), time(10, 57)),
    (time(11, 3), time(11, 57)),
    (time(12, 3), time(12, 57)),
    (time(13, 3), time(13, 25)), # Restriction: All levels discard and bot pause
]


def isWithinAllowableTradingWindow(priceTimestamp: datetime) -> bool:
    """Check if the current time is within any of the allowed ranges."""
    return any(start <= priceTimestamp.time() <= end for start, end in ALLOWED_TIMES)

