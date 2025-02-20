import os
import random
from datetime import datetime
import pandas as pd
import pytz
from lightweight_charts import Chart

from orcaven.algorithm.abc_validator.orca_enums import Symbols, TradingPosition, TeamWay
from orcaven.clients.logger.logger import config_logging

logger = config_logging(__name__)


AVAILABLE_SYMBOL = [symbol.name for symbol in Symbols]
GRAPH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "graph")
BAR_DATA_DIR = os.path.join(GRAPH_DIR, "bar_data")
OUTPUT_DIR = os.path.join(GRAPH_DIR, "output")


class ABCChart:
    def __init__(
        self, file_name: str, symbol="NQ", timeframe="5min", trading_position="Long"
    ):
        self.chart = Chart(toolbox=True)
        self.chart.legend(True)
        self.symbol = symbol
        self.timeframe = timeframe
        self.file_name = file_name

        self.chart.events.search += self.on_search

        self.trade_cleared = False
        self.chart.topbar.textbox(
            "file_name", f"{file_name} - {trading_position}", align="right"
        )
        # TODO: fix hide the lines, it is not working as expected, it is only hide the markers
        # self.chart.topbar.button("hide", "Hide", align="left", func=self.hide_trades)

        self.chart.topbar.textbox("symbol", self.symbol)
        self.chart.topbar.switcher(
            "timeframe",
            #  "1hr"
            ("line", "1sec", "10sec", "30sec", "1min", "5min", "30min"),
            default=self.timeframe,
            func=self.on_timeframe_selection,
        )

        # Load the bar data, periodic data and set the chart
        self.df = self.get_bar_data(self.symbol, "line")
        self.chart.set(self.df)

    def on_search(self, searched_string):
        """Called when the user searches."""
        new_data = self.get_bar_data(
            searched_string, self.chart.topbar["timeframe"].value
        )
        if new_data.empty:
            return

        self.chart.topbar["symbol"].set(searched_string)
        self.chart.set(new_data)

    def hide_trades(self, event=None):
        """Called when the user clicks the hide button."""
        self.chart.clear_markers()
        self.trade_cleared = True

    def on_timeframe_selection(self, event=None):
        """Called when the user changes the timeframe."""
        new_data = self.get_bar_data(
            self.chart.topbar["symbol"].value, self.chart.topbar["timeframe"].value
        )
        if new_data.empty:
            return

        if self.chart.topbar["timeframe"].value == "line":
            line = self.chart.create_line(f"{self.symbol} 1")
            sma_data = self.calculate_sma(period=1)
            line.set(sma_data)
        else:
            for i in self.chart.lines():
                # todo: make it generic
                if "NQ" in i.name:
                    i.delete()

        if self.trade_cleared:
            self.trade_cleared = False
            self.plot_trades(self.data)

        self.chart.set(new_data, True)

    def on_horizontal_line_move(self, line):
        logger.info(f"Horizontal line moved to: {line.price}")

    def get_bar_data(self, symbol, timeframe):
        """
        Retrieves bar data for a given symbol from a CSV file.
        """
        # TODO: at the moment, only NQ is available
        if symbol not in AVAILABLE_SYMBOL:
            logger.error(f'No data for "{symbol}"')
            return pd.DataFrame()
        return pd.read_csv(
            f"{BAR_DATA_DIR}/{symbol}/{self.file_name}/{symbol}_{timeframe}.csv"
        )

    @staticmethod
    def get_random_dates(list_of_dicts, num_dates):
        """Generate a random subset of dates from a list of dictionaries."""
        if num_dates > len(list_of_dicts):
            raise ValueError(
                "num_dates cannot be greater than the length of list_of_dicts"
            )

        dates = [d["date"] for d in list_of_dicts]
        random_dates = random.sample(dates, num_dates)

        return random_dates

    @staticmethod
    def get_random_dates_as_datetime(list_of_dicts, num_dates):
        """Generate a random subset of datetime objects from a list of dictionaries."""
        if num_dates > len(list_of_dicts):
            raise ValueError(
                "num_dates cannot be greater than the length of list_of_dicts"
            )

        dates = [
            datetime.fromisoformat(d["date"].replace("Z", "+00:00"))
            for d in list_of_dicts
        ]

        random.shuffle(dates)
        random_dates = random.sample(dates, num_dates)

        return random_dates

    # @staticmethod
    # def read_csv_to_dict_list(path):
    #     """Example function that reads a CSV file into a list of dictionaries."""
    #     return

    @staticmethod
    def convert_to_midnight_utc(original_str):
        """Convert a datetime string to midnight UTC."""
        dt = datetime.strptime(original_str, "%Y-%m-%d %H:%M:%S")
        dt_utc = dt.replace(tzinfo=pytz.utc)
        return dt_utc.isoformat()

    def calculate_sma(self, period: int = 50):
        return pd.DataFrame(
            {"time": self.df["date"], f"{self.symbol} {period}": self.df["close"]}
        ).dropna()

    def plot_trades(self, all_data):
        """Plot trades on the chart based on provided dates."""

        def plot_trade(trade, color, line_color):
            """Helper function to plot a single trade."""
            triggered = datetime.fromisoformat(
                self.convert_to_midnight_utc(trade["Triggered"].replace("Z", "+00:00"))
            )
            closed = datetime.fromisoformat(
                self.convert_to_midnight_utc(trade["Closed"].replace("Z", "+00:00"))
            )
            B_time = datetime.fromisoformat(
                self.convert_to_midnight_utc(trade["B_time"].replace("Z", "+00:00"))
            )
            A_time = datetime.fromisoformat(
                self.convert_to_midnight_utc(trade["A_time"].replace("Z", "+00:00"))
            )
            C_time = datetime.fromisoformat(
                self.convert_to_midnight_utc(trade["C_time"].replace("Z", "+00:00"))
            )
            o_point = trade["Order_point"]
            close_point = trade["ClosedPrice"]

            self.chart.trend_line(
                triggered,
                o_point,
                closed,
                close_point,
                round=True,
                line_color=line_color,
            )
            self.chart.marker(
                triggered,
                shape="arrow_up",
                color=color,
                text=f"{i}_{o_point}",
                position="inside",
            )
            self.chart.marker(
                closed,
                shape="square",
                color=color,
                text=f"{i}_{close_point}",
                position="inside",
            )
            self.chart.marker(
                B_time,
                shape="circle",
                color=color,
                text=f"{i}_B",
                position="inside",
            )
            self.chart.marker(
                A_time,
                shape="circle",
                color=color,
                text=f"{i}_A",
                position="inside",
            )
            self.chart.marker(
                C_time,
                shape="circle",
                color=color,
                text=f"{i}_C",
                position="inside",
            )

        for i, row in enumerate(all_data):
            if (
                row.get("Result", "NotTriggered") == "NotTriggered"
                or row.get("Triggered") == ""
            ):
                continue

            trade_color = "red" if row["Result"] == "Lost" else "green"
            line_color = "red" if row["Result"] == "Lost" else "green"

            plot_trade(row, trade_color, line_color)

    def run(self, data):
        """Run the chart with given data."""
        # dates = self.read_csv_to_dict_list(data_path)
        self.data = data
        self.plot_trades(data)
        self.chart.horizontal_line(200, func=self.on_horizontal_line_move)
        self.chart.show(block=True)

    def read_csv_to_dict_list(self, data_path):
        pass


def get_last_created_folder(symbol, way):
    symbol_path = os.path.join(OUTPUT_DIR, symbol, way, "Normal")
    try:
        items = os.listdir(symbol_path)
        dirs = [
            item for item in items if os.path.isdir(os.path.join(symbol_path, item))
        ]

        # Sort directories by creation time (newest first)
        dirs.sort(key=lambda x: os.path.getctime(os.path.join(symbol_path, x)))
        if dirs:
            return os.path.join(symbol_path, dirs[-1])
        else:
            return None
    except FileNotFoundError:
        raise FileNotFoundError(f"Path {symbol_path} not found")


def get_data(auto, symbol, way, trading_position, file_name=None):
    filename, symbol_path = None, None
    if not auto and not file_name:
        raise ValueError("file_name is required if auto is False")
    if auto:
        latest_folder = get_last_created_folder(symbol, way.value)

        for _filename in os.listdir(f"{latest_folder}"):
            file_path = os.path.join(latest_folder, _filename)
            # Check if it's a file and starts with 'Reverse_Short_'
            if os.path.isfile(file_path) and _filename.startswith(
                f"{way.value}_{trading_position}_"
            ):
                symbol_path = file_path
                break
    else:
        if not file_name:
            raise ValueError("file_name is required if auto is False")

        symbol_path = os.path.join(OUTPUT_DIR, symbol, way.value, "Normal", file_name)

        for _filename in os.listdir(f"{symbol_path}"):
            file_path = os.path.join(symbol_path, _filename)
            # Check if it's a file and starts with 'Reverse_Short_'
            if os.path.isfile(file_path) and _filename.startswith(
                f"{way.value}_{trading_position}_"
            ):
                symbol_path = file_path
                break

    logger.info(f"Auto: {AUTO}, loading data from: {symbol_path}")
    return pd.read_csv(symbol_path).to_dict("records")


def get_data_v2(auto, symbol, way, trading_position, file_name=None):
    if not auto and not file_name:
        raise ValueError("file_name is required if auto is False")

    # Determine the folder path based on `auto` flag
    if auto:
        latest_folder = get_last_created_folder(symbol, way.value)
        base_path = latest_folder
    else:
        base_path = os.path.join(OUTPUT_DIR, symbol, way.value, "Normal", file_name)

    # List files in the directory
    for _filename in os.listdir(base_path):
        file_path = os.path.join(base_path, _filename)

        # Check if it's a file and matches the required pattern
        if os.path.isfile(file_path) and _filename.startswith(
            f"{way.value}_{trading_position}_"
        ):
            logger.info(f"Auto: {auto}, loading data from: {file_path}")
            return pd.read_csv(file_path).to_dict("records")

    raise FileNotFoundError(f"No matching file found in {base_path}")


if __name__ == "__main__":
    symbol = "NQ"
    trading_position = TradingPosition.Long.value

    # This is for the generating the line and bar graph of the specific file.
    file_name_bar = "NQ-Sep-10-NQ 09-24.Last"

    # to get the trades from the csv file which we generat via runnign the backtesting.
    folder_name_trades = "NQ-Sep-10-NQ 09-24.Last"

    way = TeamWay.BreakThrough
    AUTO = True
    data = get_data(AUTO, symbol, way, trading_position, folder_name_trades)
    trading_chart = ABCChart(file_name_bar, symbol)
    trading_chart.run(data)
