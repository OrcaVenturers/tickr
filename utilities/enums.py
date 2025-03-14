from enum import Enum


# Define an Enum for event types
class EventType(Enum):
    POSITION_CLOSE = "POSITION_CLOSE"
    PENDING_ORDER = "PENDING_ORDER"
