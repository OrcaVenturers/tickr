from datetime import datetime, time, date
import os
from pydantic import BaseModel
from tabulate import tabulate

class PendingOrderInventory(BaseModel):
    orderId: str  # Unique identifier for the pending order
    instrument: str
    orderType: str
    price: float
    fibRatioLevel: float
    takeProfit: float
    stopLoss: float
    generatedAt: str
    systemTimeStamp: str


class PositionOpen(BaseModel):
    instrument: str
    fibRatioLevel: float
    positionType: str
    positionEntryPrice: float
    positionEntryTime: str
    systemTimeStamp: str
    takeProfit: float
    stopLoss: float

class PositionClose(BaseModel):
    metadata: PositionOpen
    positionClosingPrice: float
    positionClosingTime: str
    systemTimeStamp: str
    outcome: str
    net: float
