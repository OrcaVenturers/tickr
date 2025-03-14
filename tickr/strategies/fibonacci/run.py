from redis.cluster import RedisCluster
from rich import print
import sys
import datetime
from datetime import datetime, date
import time
import os
from pydantic import BaseModel
from typing import List, Optional
import redis
import json
from termcolor import colored, cprint
import uuid
from nt8.client import NTClient
from nt8.enums import OrderTypes, ActionTypes
from core.order import Order
from tqdm import tqdm

from tickr.strategies.fibonacci.config import settings
from tickr.strategies.fibonacci.schemas import PendingOrderInventory, PositionClose, PositionOpen
from tickr.strategies.fibonacci.reporting import print_position_close_table, print_position_summary_table
from loguru import logger
from tickr.strategies.RedisClient import get_redis_client
from tabulate import tabulate
from tickr.strategies.utils import timeit
import typer


app = typer.Typer()


def round_to_nearest_quarter(value):
    return round(value * 4) / 4

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

        # Round the level to the nearest 0.25 increment
        fib_levels[ratio] = round_to_nearest_quarter(level)

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
    def __init__(
        self,
        point_a: float,
        point_b: float,
        instrument: str,
        quantity: int,
        take_profit: int,
        stop_loss: int,
        reactivation_distance: float,
        nt_account: str,
        is_backtest: bool = False,
        profit_threshold: float = None,
        loss_threshold: float = None,
        log_file: str = f"trades/logs.{datetime.now()}.csv"
    ):
        # Initialize with provided points
        self.POINT_A = point_a
        self.POINT_B = point_b
        self.INSTRUMENT = instrument
        self.QUANTITY = quantity
        self.TP = take_profit
        self.SL = stop_loss
        self.REACTIVATION_DISTANCE = reactivation_distance
        self.NT_ACCOUNT = nt_account
        self.is_backtest = is_backtest
        self.profit_threshold = profit_threshold
        self.loss_threshold = loss_threshold
        
        if self.POINT_A is None or self.POINT_B is None:
            raise ValueError("Point A and Point B must be provided")
            
        self.fib_levels = calculate_fib_levels(
            point_a=self.POINT_A,
            point_b=self.POINT_B
        )
        self.isTradingZoneActive = False
        self.client: Optional[RedisCluster] = None
        self.ntclient = NTClient()

        self.active_levels = {level: False for level in self.fib_levels}
        self.last_price = None
        self.log_file = log_file
        self.open_positions: List[PositionOpen] = []
        self.closed_positions: List[PositionClose] = []
        self.internal_pending_orders_inventory: List[PendingOrderInventory] = []
        self.orders_placed_ninjatrader: List[Order] = []
        self.order_to_position_map: dict = {}
        self.total_pnl = 0.0
        
        # Print initial setup using tabulate
        print("\nFibonacci Trading Bot Configuration")
        print("=" * 50)
        
        # Basic parameters table
        params_data = [
            ["Mode", "Backtest" if self.is_backtest else "Production"],
            ["Instrument", self.INSTRUMENT],
            ["Point A", self.POINT_A],
            ["Point B", self.POINT_B],
            ["Quantity", self.QUANTITY],
            ["Take Profit", self.TP],
            ["Stop Loss", self.SL],
            ["Reactivation Distance", self.REACTIVATION_DISTANCE],
            ["NinjaTrader Account", self.NT_ACCOUNT]
        ]
        print(tabulate(params_data, headers=["Parameter", "Value"], tablefmt="simple_grid"))
        
        # Fibonacci levels table
        print("\nFibonacci Levels")
        print("=" * 50)
        fib_data = [[ratio, price] for ratio, price in self.fib_levels.items()]
        print(tabulate(fib_data, headers=["Ratio", "Price Level"], tablefmt="simple_grid"))
        
        logger.success("Bot initialized and ready to process price stream")

    def place_order_on_ninjatrader(self, order_type: str, price: float, tick_timestamp: datetime):
        """Place an order directly with NinjaTrader"""
        if not self.isTradingZoneActive:
            logger.warning(f"{tick_timestamp}: Skipping NinjaTrader order placement - outside trading window")
            return None
            
        try:
            action = ActionTypes.BUY.value if order_type == "LONG" else ActionTypes.SELL.value
            order = Order(
                instrument_name=self.INSTRUMENT,
                action=action,
                quantity=self.QUANTITY,
                price=price,
                strategy=f"{self.TP}_{self.SL}"
            )
            
            # Only place actual NinjaTrader orders in production mode
            if not self.is_backtest:
                order.place(self.ntclient, self.NT_ACCOUNT)
                logger.success(f"{tick_timestamp}: Placed {order_type} order on NinjaTrader at price: {price}")
            else:
                logger.info(f"{tick_timestamp}: [BACKTEST] Would place {order_type} order on NinjaTrader at price: {price}")
                
            self.orders_placed_ninjatrader.append(order)
            print(self.orders_placed_ninjatrader)
            return order
        except Exception as e:
            logger.error(f"Error placing NinjaTrader order: {e}")
            return None

    def cancel_all_orders(self):
        """Cancel all active orders"""
        for order in self.orders_placed_ninjatrader:
            try:
                if not self.is_backtest:
                    order.cancel(self.ntclient, self.NT_ACCOUNT)
                    logger.warning(f"Cancelled order on NinjaTrader")
                else:
                    logger.info("[BACKTEST] Would cancel order on NinjaTrader")
            except Exception as e:
                logger.error(f"Error cancelling order: {e}")
        self.orders_placed_ninjatrader.clear()
        self.internal_pending_orders_inventory.clear()
        logger.warning("All active orders cancelled")

    def enter_position(self, level, positionType, price, tick_timestamp, order_id: str):
        """Enter a position when a pending order is hit"""
        self.active_levels[level] = False
        logger.warning(f"{tick_timestamp}: Deactivated ratio. {level} until (`price > {price + self.REACTIVATION_DISTANCE}` OR `price < {price - self.REACTIVATION_DISTANCE}`)")
        print(self.active_levels)

        if self.isTradingZoneActive:
            logger.success(f"{tick_timestamp}: Entering {positionType} position at ratio:{level} - Price:{price}")
            if positionType == "LONG":
                positionTakeProfit = price + self.TP
                positionStopLoss = price - self.SL
            elif positionType == "SHORT":
                positionTakeProfit = price - self.TP
                positionStopLoss = price + self.SL
            
            # Create open position
            open_position = PositionOpen(
                instrument = self.INSTRUMENT,
                fibRatioLevel = level,
                positionType = positionType,
                positionEntryPrice = price,
                positionEntryTime = str(tick_timestamp),
                systemTimeStamp = str(datetime.now()),
                takeProfit = positionTakeProfit,
                stopLoss = positionStopLoss
            )
            self.open_positions.append(open_position)
            print(self.open_positions)
            
            # Map the order to the position
            self.order_to_position_map[order_id] = open_position
            print(self.order_to_position_map)
            # Remove the pending order that was hit
            self.internal_pending_orders_inventory = [order for order in self.internal_pending_orders_inventory if order.orderId != order_id]
        else:
            logger.debug(f"{tick_timestamp}: Position Entry void at level: {level} - Outside trading window zone")

    def generate_pending_orders(self, order_type, fib_level, fib_level_price, tick_timestamp):
        if not self.isTradingZoneActive:
            logger.debug(f"{tick_timestamp}: Skipping pending order generation - outside trading window")
            return
            
        logger.debug(f"{tick_timestamp}: Placed Pending Order: {order_type} at price: {fib_level_price}")
        if order_type == "BUY":
            takeProfit = fib_level_price + self.TP
            stopLoss = fib_level_price - self.SL
        elif order_type == "SELL":
            takeProfit = fib_level_price - self.TP
            stopLoss = fib_level_price + self.SL
                # Place the order directly
        order: Optional[Order] = self.place_order_on_ninjatrader(order_type, fib_level_price, tick_timestamp)
        if order:
            order_id = str(uuid.uuid4())
            pendingOrderGenerated = PendingOrderInventory(
                orderId=order_id,  # Use the generated order ID
                instrument=self.INSTRUMENT,
                orderType=order_type,
                price=fib_level_price,
                fibRatioLevel=fib_level,
                takeProfit=takeProfit,
                stopLoss=stopLoss,
                generatedAt=str(tick_timestamp),
                systemTimeStamp=str(datetime.now()),
            )
            self.internal_pending_orders_inventory.append(pendingOrderGenerated)
            print(self.internal_pending_orders_inventory)
            logger.debug(f"{tick_timestamp}: Added to internal pending order inventory with ID: {order_id}")

    def process_price(self, current_price, tick_timestamp: datetime):
        # Update trading window status
        was_in_trading_window = self.isTradingZoneActive
        self.isTradingZoneActive = settings.isWithinAllowableTradingWindow(tick_timestamp)
        
        # If we just left the trading window, cancel all orders
        if was_in_trading_window and not self.isTradingZoneActive:
            logger.warning(f"{tick_timestamp}: Trading window ended, cancelling all orders")
            self.cancel_all_orders()
        
        # If we just entered the trading window, place orders for active levels
        if not was_in_trading_window and self.isTradingZoneActive:
            logger.info(f"{tick_timestamp}: Trading window started, placing orders for active levels")
            for fib_level, is_active in self.active_levels.items():
                print(self.active_levels)
                if is_active:
                    fib_level_price = self.fib_levels[fib_level]
                    pending_order_type = "SELL" if fib_level_price > current_price else "BUY"
                    self.generate_pending_orders(pending_order_type, fib_level, fib_level_price, tick_timestamp)
        
        if self.last_price is None:
            self.last_price = current_price
            return

        # Check if any pending orders were hit
        for pending_order in self.internal_pending_orders_inventory[:]:  # Use slice copy to avoid modification during iteration
            if min(self.last_price, current_price) <= pending_order.price <= max(self.last_price, current_price):
                position_type = "LONG" if pending_order.orderType == "BUY" else "SHORT"
                self.enter_position(
                    level=pending_order.fibRatioLevel,
                    positionType=position_type,
                    price=current_price,
                    tick_timestamp=tick_timestamp,
                    order_id=pending_order.orderId
                )

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

        self.reactivate_levels(current_price, tick_timestamp)
        self.last_price = current_price

    def get_total_pnl(self) -> float:
        """Get the current total profit and loss"""
        return self.total_pnl

    def print_pnl_summary(self):
        """Print a summary of the current P&L status"""
        cprint(f"\nCurrent Total P&L: {self.total_pnl:+.2f}", "black", "on_white")
        print(f"Number of Closed Positions: {len(self.closed_positions)}")
        if self.closed_positions:
            winning_trades = sum(1 for pos in self.closed_positions if pos.outcome == "PROFIT")
            losing_trades = sum(1 for pos in self.closed_positions if pos.outcome == "LOSS")
            win_rate = (winning_trades / len(self.closed_positions)) * 100
            print(f"Win Rate: {win_rate:.1f}% ({winning_trades}/{len(self.closed_positions)})")

    def close_position(self, position, result, profit_loss, current_price, tick_timestamp):
        self.open_positions.remove(position)
        print(self.open_positions)
        # Remove any associated orders from the map
        self.order_to_position_map = {k: v for k, v in self.order_to_position_map.items() if v != position}
        print(self.order_to_position_map)
        
        closed_position = PositionClose(
            metadata=position,
            positionClosingPrice=current_price,
            positionClosingTime= str(tick_timestamp),
            systemTimeStamp = str(datetime.now()),
            outcome=result,
            net=profit_loss
        )
        self.closed_positions.append(closed_position)
        print(self.closed_positions)
        # Update total P&L
        self.total_pnl += profit_loss
        
        # Check profit/loss thresholds
        if (self.profit_threshold is not None and self.total_pnl >= self.profit_threshold) or \
           (self.loss_threshold is not None and self.total_pnl <= self.loss_threshold):
            logger.warning(f"{'Profit' if self.total_pnl >= 0 else 'Loss'} threshold reached ({self.total_pnl}). Stopping trading.")
            self.cancel_all_orders()
            if not self.is_backtest:
                sys.exit(0)
            return
        
        # Print position close and current P&L status
        highlighted_message_color = "on_green" if closed_position.outcome == "PROFIT" else "on_red"
        cprint(f"{tick_timestamp}: Position closed/flatten at {current_price} - {result}: {profit_loss}", "black", highlighted_message_color)
        print(closed_position)
        self.print_pnl_summary()  # Print updated P&L summary after each position close

    def reactivate_levels(self, current_price, tick_timestamp):
        for fib_level, fib_level_price in self.fib_levels.items():
            if not self.active_levels[fib_level]:  # Only check inactive levels
                if abs(current_price - fib_level_price) >= self.REACTIVATION_DISTANCE:
                    self.active_levels[fib_level] = True
                    logger.info(
                        f"{tick_timestamp}: Reactivated Fib. ratio: {fib_level} ({fib_level_price}) at - current price: {current_price}")
                    print(self.active_levels)
                    pending_order_type = "SELL" if fib_level_price > current_price else "BUY"
                    self.generate_pending_orders(pending_order_type, fib_level, fib_level_price, tick_timestamp)

    def production(self):
        self.client = get_redis_client()
        pubsub = self.client.pubsub()
        pubsub.subscribe(settings.REDIS_PRICE_STREAM_CHANNEL)
        running = True
        logger.debug("Listening for price stream...")
        try:
            while running:
                message = pubsub.get_message(timeout=1)
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
            logger.error("Error in main price streaming loop. Cancelling all orders")
            self.cancel_all_orders()
            pubsub.close()
            self.client.close()
            self.ntclient.Dispose()
            logger.success("Subscriber closed.")

    def backtest(self, path):
        price_stream = stream_file(file_path=path)
        for row in price_stream:
            parts = row.split(';')
            if len(parts) < 2:
                continue
            try:
                _timestamp = parts[0]
                formatted_date_str = _timestamp[:-1]
                dt = datetime.strptime(formatted_date_str, "%Y%m%d %H%M%S %f")
                current_price = float(parts[1])
                self.process_price(current_price, tick_timestamp=dt)
            except ValueError:
                continue
        logger.success("Generating P&L statement for overall backtesting")
        print_position_close_table(self.closed_positions)
        print_position_summary_table(self.closed_positions)

@app.command()
def production(
    point_a: float = typer.Option(..., help="Point A for Fibonacci calculation"),
    point_b: float = typer.Option(..., help="Point B for Fibonacci calculation"),
    instrument: str = typer.Option(..., help="Trading instrument (e.g., 'NQ SEP24')"),
    quantity: int = typer.Option(2, help="Number of contracts to trade"),
    take_profit: int = typer.Option(15, help="Take profit in points"),
    stop_loss: int = typer.Option(20, help="Stop loss in points"),
    reactivation_distance: float = typer.Option(..., help="Distance to reactivate Fibonacci levels"),
    nt_account: str = typer.Option("APEX2948580000003", help="NinjaTrader account number"),
    config_file: str = typer.Option("configs/es.dev.json", help="Path to configuration file"),
    profit_threshold: float = typer.Option(None, help="Stop trading if total profit exceeds this value"),
    loss_threshold: float = typer.Option(None, help="Stop trading if total loss exceeds this value (provide as positive number)"),
):
    """Run the Fibonacci trading bot in production mode"""
    bot = FibonacciTradingBot(
        point_a=point_a,
        point_b=point_b,
        instrument=instrument,
        quantity=quantity,
        take_profit=take_profit,
        stop_loss=stop_loss,
        reactivation_distance=reactivation_distance,
        nt_account=nt_account,
        is_backtest=False,
        profit_threshold=profit_threshold,
        loss_threshold=loss_threshold if loss_threshold is None else -abs(loss_threshold)
    )
    
    # Add startup timer
    print("\nStarting bot in 10 seconds...")
    for _ in tqdm(range(10), desc="Startup", unit="s"):
        time.sleep(1)
    print("\nBot is now running...")
    
    bot.production()

@app.command()
def backtest(
    filepath: str = typer.Option(..., help="Path to the backtest data file"),
    point_a: float = typer.Option(..., help="Point A for Fibonacci calculation"),
    point_b: float = typer.Option(..., help="Point B for Fibonacci calculation"),
    instrument: str = typer.Option(..., help="Trading instrument (e.g., 'NQ SEP24')"),
    quantity: int = typer.Option(2, help="Number of contracts to trade"),
    take_profit: int = typer.Option(15, help="Take profit in points"),
    stop_loss: int = typer.Option(20, help="Stop loss in points"),
    reactivation_distance: float = typer.Option(..., help="Distance to reactivate Fibonacci levels"),
    nt_account: str = typer.Option("APEX2948580000003", help="NinjaTrader account number"),
    config_file: str = typer.Option("configs/es.dev.json", help="Path to configuration file"),
    profit_threshold: float = typer.Option(None, help="Stop trading if total profit exceeds this value"),
    loss_threshold: float = typer.Option(None, help="Stop trading if total loss exceeds this value (provide as positive number)"),
):
    """Run the Fibonacci trading bot in backtest mode"""
    if not filepath:
        typer.echo("No filepath defined? Please define using --filepath flag")
    else:
        typer.echo(f"\nRunning backtesting on dataset: {filepath}")
        
        bot = FibonacciTradingBot(
            point_a=point_a,
            point_b=point_b,
            instrument=instrument,
            quantity=quantity,
            take_profit=take_profit,
            stop_loss=stop_loss,
            reactivation_distance=reactivation_distance,
            nt_account=nt_account,
            is_backtest=True,
            profit_threshold=profit_threshold,
            loss_threshold=loss_threshold if loss_threshold is None else -abs(loss_threshold)
        )
        
        bot.backtest(filepath)

if __name__ == "__main__":
    app()