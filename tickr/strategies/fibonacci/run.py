from redis.cluster import RedisCluster
from rich import print
import sys
import pandas as pd
import datetime
from datetime import datetime, time, date
import os
from pydantic import BaseModel
from typing import List, Optional
import redis
import json
from termcolor import colored, cprint
from tickr.strategies.fibonacci.discord import *
from tickr.strategies.fibonacci.config import settings
from tickr.strategies.fibonacci.schemas import PendingOrder, PositionClose, PositionOpen
from tickr.strategies.fibonacci.reporting import print_position_close_table, print_position_summary_table
from loguru import logger
from tickr.strategies.RedisClient import get_redis_client, send_notification
from tabulate import tabulate
from tickr.strategies.utils import timeit
import typer

app = typer.Typer()


def calculate_fib_levels(point_a, point_b):
    # Calculate the difference between Point A and Point B
    difference = point_a - point_b
    ratios = settings.FIBONACCI_RATIOS

    # Calculate the levels for each ratio
    fib_levels = {}
    for ratio in ratios:
        if ratio >= 0:
            level = point_b + (difference * ratio)
        else:
            level = point_b - (difference * abs(ratio))

        # Round the level to the nearest integer
        fib_levels[ratio] = round(level)
    return fib_levels


def is_valid_file_path(file_path):
    """Check if the file path is valid, exists, and readable."""
    return os.path.isfile(file_path) and os.access(file_path, os.R_OK)

def stream_file(file_path):
    """Read the file line by line to simulate streaming data."""
    if not is_valid_file_path(file_path):
        raise FileNotFoundError(f"Error: Cannot read file at {file_path}")

    with open(file_path, 'r') as file:
        for line in file:
            yield line.strip()


class FibonacciTradingBot:
    def __init__(self, log_file=f"trades/logs.{datetime.now()}.csv"):
        self.POINT_A = float('-inf')
        self.POINT_B = float('inf')
        self.fib_levels = None
        self.TP = settings.TradeExecutionSettings.takeProfit
        self.SL = settings.TradeExecutionSettings.stopLoss
        self.REACTIVATION_DISTANCE = settings.TradeExecutionSettings.reactivationDistance
        self.precalculations = True
        self.isTradingZoneActive = True
        self.client: Optional[RedisCluster] = get_redis_client()

        self.active_levels = None
        self.last_price = None
        self.log_file = log_file
        self.open_positions: List[PositionOpen] = []
        self.closed_positions: List[PositionClose] = []
        self.pending_orders: List[PendingOrder] = []
        logger.success("Processing price stream - waiting for Point A/B calculation")

    def enter_position(self, level, order_type, price, tick_timestamp):
        self.active_levels[level] = False
        logger.warning(f"{tick_timestamp}: Deactivated ratio. {level} until (`price > {price + self.REACTIVATION_DISTANCE}` OR `price < {price - self.REACTIVATION_DISTANCE}`)")
        reactivation_upper = price + self.REACTIVATION_DISTANCE
        reactivation_lower = price - self.REACTIVATION_DISTANCE

        if self.isTradingZoneActive:
            logger.success(f"{tick_timestamp}: Entering {order_type} position at ratio:{level} - Price:{price}")
            if order_type == "LONG":
                positionTakeProfit = price + self.TP
                positionStopLoss = price - self.SL
            elif order_type == "SHORT":
                positionTakeProfit = price - self.TP  # Take Profit
                positionStopLoss = price + self.SL  # Stop Loss
            open_position = PositionOpen(
                    instrument = settings.INSTRUMENT,
                    fibRatioLevel = level,
                    positionType = order_type,
                    positionEntryPrice = price,
                    positionEntryTime = str(tick_timestamp),
                    systemTimeStamp = str(datetime.now()),
                    takeProfit = positionTakeProfit,
                    stopLoss = positionStopLoss
                )
            self.open_positions.append(open_position)
        else:
            logger.error(f"Position Entry void at level: {level} Outside trading window zone")


    def generate_pending_orders(self, order_type, fib_level, fib_level_price, tick_timestamp):
        logger.info(f"{tick_timestamp}: Placed Limit Pending Order: {order_type} at price: {fib_level_price}")
        if order_type == "BUY":
            takeProfit = fib_level_price + self.TP
            stopLoss = fib_level_price - self.SL
        elif order_type == "SELL":
            takeProfit = fib_level_price - self.TP
            stopLoss = fib_level_price + self.SL
        pendingOrderGenerated = PendingOrder(
                instrument = settings.INSTRUMENT,
                orderType=order_type,
                price=fib_level_price,
                fibRatioLevel=fib_level,
                takeProfit=takeProfit,
                stopLoss=stopLoss,
                generatedAt=str(tick_timestamp),
                systemTimeStamp=str(datetime.now()),
            )
        self.pending_orders.append(
            pendingOrderGenerated
        )
        send_notification(
            self.client,
            stream=settings.ORDERS_NOTIFICATIONS_STREAM,
            event = "PENDING_ORDER",
            notification = {
                "metadata": pendingOrderGenerated.model_dump(),
                "Instrument": settings.INSTRUMENT,
                "AtmStrategy": f"{self.TP}_{self.SL}"
            }
        )
        send_notification(
            self.client,
            stream=settings.DISCORD_NOTIFICATIONS_STREAM,
            event = "PENDING_ORDER",
            notification=pendingOrderGenerated.model_dump()
        )

    def precalculations_phase(self, current_price, tick_timestamp) -> bool:
        start_time = settings.CandlestickComputationTime.start
        end_time = settings.CandlestickComputationTime.end

        def printFibonnaciLevels(fib_levels):
            table_data = [[key, value] for key, value in fib_levels.items()]
            headers = ["Fib Ratio", "Level"]
            print(tabulate(table_data, headers=headers, tablefmt="simple_grid"))

        if start_time <= tick_timestamp.time() <= end_time:
            self.precalculations = True
            self.POINT_A = max(self.POINT_A, current_price)
            self.POINT_B = min(self.POINT_B, current_price)
            return self.precalculations
        elif tick_timestamp.time() > end_time:
            self.precalculations = False
            self.POINT_A = self.POINT_A if settings.CandlestickKickoffPoints.POINT_A is None else settings.CandlestickKickoffPoints.POINT_A
            self.POINT_B = self.POINT_B if settings.CandlestickKickoffPoints.POINT_B is None else settings.CandlestickKickoffPoints.POINT_B
            self.fib_levels = calculate_fib_levels(
                point_a=self.POINT_A,
                point_b=self.POINT_B
            )
            self.active_levels = {level: False for level in self.fib_levels}
            print(f"POINT A: {self.POINT_A}, POINT B: {self.POINT_B}")
            printFibonnaciLevels(self.fib_levels)
            send_notification(
                self.client,
                stream=settings.DISCORD_NOTIFICATIONS_STREAM,
                event="KICKOFF",
                notification= {
                    "POINT_A": self.POINT_A,
                    "POINT_B": self.POINT_B,
                    "INSTRUMENT": settings.INSTRUMENT,
                    "FIBONACCI": self.fib_levels
                }
            )
            return self.precalculations
        else: # If price is before 2.30pm (ignore)
            self.precalculations = True
            return self.precalculations

    # @timeit
    def process_price(self, current_price, tick_timestamp: datetime):
        self.isTradingZoneActive: bool = settings.isWithinAllowableTradingWindow(tick_timestamp)
        if self.precalculations:
            self.precalculations_phase(current_price, tick_timestamp)
            return

        if self.last_price is None:
            self.last_price = current_price
            return


        # Analysis of open positions and marking as close if hit TP/SL
        for position in self.open_positions[:]:
            if (position.positionType == "LONG" and current_price >= position.takeProfit) or (
                    position.positionType == "SHORT" and current_price <= position.takeProfit):
                profit = +abs(position.takeProfit - position.positionEntryPrice)
                self.close_position(position, "PROFIT", profit, current_price, tick_timestamp)
            elif (position.positionType == "LONG" and current_price <= position.stopLoss) or (
                    position.positionType == "SHORT" and current_price >= position.stopLoss):
                loss = -abs(position.stopLoss - position.positionEntryPrice)
                self.close_position(position, "LOSS", loss, current_price, tick_timestamp)

        # Entering LONG/SHORT position and deactivating fib levels
        for level, fib_level_price in self.fib_levels.items():
            if self.active_levels[level] and (min(self.last_price, current_price) <= fib_level_price <= max(self.last_price, current_price)):
                order_type = "SHORT" if self.last_price < current_price else "LONG"
                self.enter_position(level, order_type, fib_level_price, tick_timestamp)

        self.reactivate_levels(current_price, tick_timestamp)
        self.last_price = current_price

    def close_position(self, position, result, profit_loss, current_price, tick_timestamp):
        if self.isTradingZoneActive:
            self.open_positions.remove(position)
            closed_position = PositionClose(
                                metadata=position,
                                positionClosingPrice=current_price,
                                positionClosingTime= str(tick_timestamp),
                                systemTimeStamp = str(datetime.now()),
                                outcome=result,
                                net=profit_loss
                            )
            self.closed_positions.append(closed_position)
            highlighted_message_color = "on_green" if closed_position.outcome == "PROFIT" else "on_red"
            cprint(f"{tick_timestamp}: Position closed/flatten at {current_price} - {result}: {profit_loss}", "black", highlighted_message_color)
            print(closed_position)
            send_notification(
                self.client,
                stream=settings.DISCORD_NOTIFICATIONS_STREAM,
                event="POSITION_CLOSE",
                notification=closed_position.model_dump()
            )

    def reactivate_levels(self, current_price, tick_timestamp):
        for fib_level, fib_level_price in self.fib_levels.items():
            if not self.active_levels[fib_level]:  # Only check inactive levels
                if abs(current_price - fib_level_price) >= self.REACTIVATION_DISTANCE:
                    self.active_levels[fib_level] = True
                    logger.info(
                        f"{tick_timestamp}: Reactivated Fib. ratio: {fib_level} ({fib_level_price}) at - current price: {current_price}")

                    if self.isTradingZoneActive:
                        pending_order_type = "SELL" if fib_level_price > current_price else "BUY"  # bouncing ball
                        self.generate_pending_orders(pending_order_type, fib_level, fib_level_price, tick_timestamp)


    def production(self):
        pubsub = self.client.pubsub()
        pubsub.subscribe(settings.REDIS_PRICE_STREAM_CHANNEL)  # Listen to the channel
        # Flag to control the loop
        running = True
        logger.info("Listening for price stream...")
        try:
            while running:
                message = pubsub.get_message(timeout=1)  # Use get_message with a timeout
                if message:
                    if message["type"] == "message":
                        _data = json.loads(message['data'])
                        timestamp_dt: datetime = datetime.strptime(_data["TIMESTAMP"], "%Y-%m-%d %H:%M:%S.%f")
                        self.process_price(
                            current_price=float(_data["LAST"]),
                            tick_timestamp=timestamp_dt
                        )
        except Exception as e:
            logger.error(f"Error occurred: {e}")
        finally:
            pubsub.close()
            self.client.close()
            logger.success("Subscriber closed.")

    def backtest(self, path):
        price_stream = stream_file(file_path=path)
        for row in price_stream:
            parts = row.split(';')
            if len(parts) < 2:
                continue
            try:
                _timestamp = parts[0]
                formatted_date_str = _timestamp[:-1]  # Trim last digit to match %f format
                dt = datetime.strptime(formatted_date_str, "%Y%m%d %H%M%S %f")
                current_price = float(parts[1])
                self.process_price(current_price, tick_timestamp=dt)
            except ValueError:
                continue
        logger.success("Generating P&L statement for overall backtesting")
        print_position_close_table(self.closed_positions)
        print_position_summary_table(self.closed_positions)


@app.command()
def production():
    print(settings.model_dump())
    bot = FibonacciTradingBot()
    bot.production()


@app.command()
def backtest(filepath: Optional[str] = None):
    if not filepath:
        typer.echo("No filepath defined? Please define using --filepath flag")
    else:
        typer.echo(f"Running backtesting on dataset: {filepath}")
        bot = FibonacciTradingBot()
        bot.backtest(filepath)


if __name__ == "__main__":
    app()
