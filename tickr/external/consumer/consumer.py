from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional, Sequence
from datetime import datetime
from tabulate import tabulate
import uuid

from ..consumer.engine import ConsumerTracking, Orders, engine
import time


def isWithinAllowableTradingWindow(self, priceTimestamp: datetime) -> bool:
    """Check if the current time is within any of the allowed ranges."""
    return any(start <= priceTimestamp.time() <= end for start, end in self.ALLOWED_TIMES)


def fetch_new_orders(consumer_id: str, strategyId: str):
    """
    Fetch new orders for a consumer based on the last fetched timestamp.
    """
    with Session(engine) as session:
        consumer = session.get(ConsumerTracking, consumer_id)
        if not consumer:
            print(f"Initialising `new` consumer with ID: {consumer_id}")
            consumer = ConsumerTracking(
                consumerId=consumer_id,
                connectedAt=datetime.utcnow(),
                disconnectedAt=None,
                previousOrdersTimestamp=datetime.min
            )
            session.add(consumer)
            session.commit()
            session.refresh(consumer)

        statement = select(Orders).where(
            (Orders.strategyId == strategyId) &
            (Orders.isActive == True) &
            (Orders.lastUpdatedAt > consumer.previousOrdersTimestamp)
        )
        new_orders: Sequence[Orders]  = session.exec(statement).all()
        orders_data = [
            {
                "orderId": o.orderId,
                "strategyId": o.strategyId,
                "instrument": o.instrument,
                "price": o.price,
                "reactivationDistance": o.reactivationDistance,
                "pointA": o.pointA,
                "pointB": o.pointB,
                "fibonacciLevel": o.fibonacciLevel,
                "lastUpdatedAt": o.lastUpdatedAt
            }
            for o in new_orders
        ]

        if new_orders:
            latest_timestamp = max(order["lastUpdatedAt"] for order in orders_data)
            consumer.previousOrdersTimestamp = latest_timestamp
            session.commit()
            print(f"Updated consumer tracking with latest order timestamp: {latest_timestamp}")

            headers = ["Order ID", "Strategy ID", "Instrument", "Price", "Reactivation Distance", "Point A", "Point B", "Fibonacci Level", "Last Updated At"]
            table_data = [[o["orderId"], o["strategyId"], o["instrument"], o["price"], o["reactivationDistance"], o["pointA"], o["pointB"], o["fibonacciLevel"], o["lastUpdatedAt"]] for o in orders_data]
            print(tabulate(table_data, headers=headers, tablefmt="simple_grid"))
            print()

        return orders_data


def main(consumerId: str, strategyId: str):
    print(f"Starting consumption from consumer: {consumerId} - for strategy id: {strategyId}")
    while True:
        fetch_new_orders(consumerId, strategyId)
        time.sleep(0.02)


if __name__ == "__main__":
    consumerId = str(uuid.uuid4())
    main(consumerId, strategyId="NQ MAR25-21381.0-20996.0-30.0")