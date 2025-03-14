from enum import Enum


class Message(Enum):
    COMMAND = 0
    DATA = 1
    VALUE = 2
    CONFIRMORDERS = 3
    SUBSCRIBE = 4


class StrategyCommands(Enum):
    """Enum for trading strategy commands."""

    START = "START"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    SET_PARAMETER = "SET_PARAMETER"


class ActionTypes(Enum):
    """Enum for entry and exit action types."""

    BUY = "BUY"
    SELL = "SELL"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"

    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"

    FLAT = "FLAT"


class OrderTypes(Enum):
    """Enum for different order types."""

    MARKET = "MARKET"
    STOP_MARKET = "STOPMARKET"
    MIT = "MIT"

    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOPLIMIT"
    TRAIL_STOP = "TRAILSTOP"
    TRAIL_STOP_LIMIT = "TRAILSTOPLIMIT"


class TradingStrategy(Enum):
    """Enum for predefined trading strategies."""

    ST5PT_50SL = "ST5PT_50SL"
    ST30PT_50SL = "ST30PT_50SL"
    ST2Q2PT_20SL = "ST2Q2PT_20SL"
    ST30_PT_30SL = "ST30_PT_30SL"
    ST12PT_200SL = "ST12PT_200SL"


class NTOrderStatus(Enum):
    """Enum for the status of orders."""

    WORKING = "Working"
    ACCEPTED = "Accepted"
    SUBMITTED = "Submitted"
    FILLED = "Filled"
    PARTIALLY_FILLED = "Partiallyfilled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    EXPIRED = "Expired"
    PENDING = "Pending"
    TRIGGERED = "Triggered"
    AMENDED = "Amended"
    MARKET_ORDER = "Marketorder"


class OrcaOrderStatus(Enum):
    """Enum for the status of orders."""

    PLACED = "PLACED"
    FILLED = "FILLED"
    PENDING = "PENDING"


# Below is the AtiSocket class, as previously defined.
class MarketDataType(Enum):
    Ask = 0
    Bid = 1
    Last = 2
    DailyHigh = 3
    DailyLow = 4
    DailyVolume = 5
    LastClose = 6
    Opening = 7
    OpenInterest = 8
    Settlement = 9
    Unknown = 10


class OrderCommands(Enum):
    PLACE = 0
    CANCEL = 1
    CHANGE = 2
    CLOSEPOSITION = 3
    CLOSESTRATEGY = 4
    CANCELALLORDERS = 5
