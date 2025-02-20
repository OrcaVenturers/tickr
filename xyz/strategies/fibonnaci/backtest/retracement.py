import time
from rich import print
from loguru import logger
import sys
import pandas as pd
import datetime
import os

def calculate_fib_levels(point_a, point_b):
    # Calculate the difference between Point A and Point B
    difference = point_a - point_b
    
    # Define the Fibonacci ratios
    ratios = [0.618, 1.618, 2.92, 2.3, 2.618, 3.618, 4.92, -0.618, -1.618, -2.618, -3.618]
    
    # Calculate the levels for each ratio
    fib_levels = {}
    for ratio in ratios:
        if ratio >= 0:
            level = point_b + (difference * ratio)
        else:
            level = point_b - (difference * abs(ratio))
        
        # Round the level to the nearest integer
        fib_levels[ratio] = round(level)
    print(fib_levels)
    return fib_levels


def stream_file(file_path):
    """Read the file line by line to simulate streaming data."""
    with open(file_path, 'r') as file:
        for line in file:
            yield line.strip()
            # time.sleep(0.5)  # Simulate real-time delay

class FibonacciTradingBot:
    def __init__(self, file_path, log_file=f"trades/logs.{datetime.datetime.now()}.csv"):
        self.file_path = file_path
        self.fib_levels = calculate_fib_levels(
            point_a=21805.50, 
            point_b=21701
        )
        self.TP = 15.0
        self.SL = 15.0
        self.REACTIVATION_DISTANCE = 30.0

        self.active_levels = {level: True for level in self.fib_levels}  # All levels active initially
        self.last_price = None
        self.log_file = log_file
        self.open_trades = []  # Track open trades

        # Ensure the directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Check if log file exists, else create it
        if not os.path.exists(self.log_file):
            self.trades = pd.DataFrame(columns=[
                "Fib Ratio", "Status", "Position", "Price", "TP", "SL", "Timestamp", "Reactivation Upper", "Reactivation Lower", "Profit/Loss", "Net"
            ])
            self.trades.to_csv(self.log_file, index=False)
        else:
            self.trades = pd.read_csv(self.log_file)

    def place_order(self, level, order_type, price, tick_timestamp):
        logger.success(f"Placing {order_type} order at level {level} (Price: {price})")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # More granular timestamp
        reactivation_upper = price + self.REACTIVATION_DISTANCE
        reactivation_lower = price - self.REACTIVATION_DISTANCE
        if order_type == "LONG":
            tp = price + self.TP
            sl = price - self.SL
        elif order_type == "SHORT":
            tp = price - self.TP  # Take Profit
            sl = price + self.SL  # Stop Loss

        new_trade = {
            "Fib Ratio": level,
            "Status": "Deactivated",
            "Position": order_type,
            "Price": price,
            "TP": tp,
            "SL": sl,
            "Timestamp": tick_timestamp,
            "Reactivation Upper": reactivation_upper,
            "Reactivation Lower": reactivation_lower,
            "Profit/Loss": None,
            "Net": None
        }
        self.open_trades.append(new_trade)

        pd.DataFrame([new_trade]).to_csv(self.log_file, mode='a', header=False, index=False)

    def process_price(self, current_price, tick_timestamp):
        if self.last_price is None:
            self.last_price = current_price
            return

        for trade in self.open_trades[:]:
            if (trade["Position"] == "LONG" and current_price >= trade["TP"]) or (trade["Position"] == "SHORT" and current_price <= trade["TP"]):
                profit = +abs(trade["TP"] - trade["Price"])
                self.close_trade(trade, "Profit", profit, current_price, tick_timestamp)
            elif (trade["Position"] == "LONG" and current_price <= trade["SL"]) or (trade["Position"] == "SHORT" and current_price >= trade["SL"]):
                loss = -abs(trade["SL"] - trade["Price"])
                self.close_trade(trade, "Loss", loss, current_price, tick_timestamp)

        for level, price in self.fib_levels.items():
            if self.active_levels[level] and current_price == price:
                order_type = "SHORT" if self.last_price < current_price else "LONG"
                self.place_order(level, order_type, price, tick_timestamp)
                self.active_levels[level] = False  # Deactivate level
                logger.warning(f"Deactivated fib. level: {level} until price passes ± {self.REACTIVATION_DISTANCE} delta (`price > {price + self.REACTIVATION_DISTANCE}` OR `price < {price - self.REACTIVATION_DISTANCE}`) ")

        self.reactivate_levels(current_price, tick_timestamp)
        self.last_price = current_price

    def close_trade(self, trade, result, profit_loss, current_price, tick_timestamp):
        self.open_trades.remove(trade)
        net = profit_loss
        logger.success(f"Trade executed at {current_price}. {result}: {profit_loss}")

        executed_trade = {
            "Fib Ratio": trade["Fib Ratio"],
            "Status": "Executed",
            "Position": "Executed",
            "Price": current_price,
            "TP": trade["TP"],
            "SL": trade["SL"],
            "Timestamp": tick_timestamp,
            "Reactivation Upper": None,
            "Reactivation Lower": None,
            "Profit/Loss": result,
            "Net": net
        }

        pd.DataFrame([executed_trade]).to_csv(self.log_file, mode='a', header=False, index=False)

    def reactivate_levels(self, current_price, tick_timestamp):
        for level, price in self.fib_levels.items():
            if not self.active_levels[level]:  # Only check inactive levels
                if abs(current_price - price) > self.REACTIVATION_DISTANCE:
                    self.active_levels[level] = True  # Reactivate level
                    logger.info(f"Reactivated Fib. Level: {level} ({price}) at ± {self.REACTIVATION_DISTANCE} - Current: {current_price}")

                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    new_reactivation = pd.DataFrame([{
                        "Fib Ratio": level,
                        "Status": "Activated",
                        "Position": None,
                        "Price": current_price,
                        "TP": None,
                        "SL": None,
                        "Timestamp": tick_timestamp,
                        "Reactivation Upper": None,
                        "Reactivation Lower": None,
                        "Profit/Loss": None,
                        "Net": None
                    }])
                    new_reactivation.to_csv(self.log_file, mode='a', header=False, index=False)

    def run(self):
        price_stream = stream_file(self.file_path)
        for row in price_stream:
            parts = row.split(';')
            if len(parts) < 2:
                continue
            
            try:
                _timestamp = parts[0]
                formatted_date_str = _timestamp[:-1]  # Trim last digit to match %f format
                dt = datetime.datetime.strptime(formatted_date_str, "%Y%m%d %H%M%S %f")
                current_price = float(parts[1])
                self.process_price(current_price, tick_timestamp=dt)
            except ValueError:
                continue

                        
# Run the bot
file_path = "datasets/NQ 03-25.Last.txt"  # Update with the correct file path
bot = FibonacciTradingBot(file_path)
bot.run()
