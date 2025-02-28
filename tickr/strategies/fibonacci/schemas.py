from datetime import datetime, time, date
import os
from pydantic import BaseModel
from tabulate import tabulate

class PendingOrder(BaseModel):
    orderType: str
    price: float
    fibRatioLevel: float
    takeProfit: float
    stopLoss: float
    generatedAt: str
    systemTimeStamp: str


class PositionOpen(BaseModel):
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
