import json
from datetime import time, datetime
from pydantic import BaseModel
from typing import List, Optional, Tuple
from rich import print
import os

class Connections(BaseModel):
    REDIS_HOST: Optional[str] = "redis"
    REDIS_PORT: Optional[int] = 6379
    REDIS_PASSWORD: Optional[str] = None
    LOGGING_LEVEL: Optional[str] = "INFO"
    DISCORD_WEBHOOK_URL: Optional[str] = None

class ConfigModel(BaseModel):
    REDIS_PRICE_STREAM_CHANNEL: str
    FIBONACCI_RATIOS: List[float]
    ALLOWED_TIMES: List[Tuple[time, time]]
    CONNECTIONS: Connections

    def isWithinAllowableTradingWindow(self, priceTimestamp: datetime) -> bool:
        """Check if the current time is within any of the allowed ranges."""
        return any(start <= priceTimestamp.time() <= end for start, end in self.ALLOWED_TIMES)


CONFIG_FILE = os.getenv("CONFIG_FILE")
with open(CONFIG_FILE, "r") as f:
    config_data = json.load(f)

settings = ConfigModel(**config_data)

# Example usage
if __name__ == "__main__":
    print(settings.model_dump())
    now = datetime.now()
    print(f"Is current time {now.time()} within trading window? {settings.isWithinAllowableTradingWindow(now)}")