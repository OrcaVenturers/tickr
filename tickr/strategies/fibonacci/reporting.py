from typing import List
from tickr.strategies.fibonacci.schemas import PositionClose
from rich import print
from tabulate import tabulate

def print_position_close_table(position_closes: List[PositionClose]) -> None:
    """Prints a tabulate table from a list of PositionClose objects."""

    headers = ["Fib Ratio", "Position Type", "Entry Price", "Entry Time",
               "Closing Price", "Closing Time", "Outcome", "Net Profit/Loss"]
    table_data = []
    for pc in position_closes:
        table_data.append([
            pc.metadata.fibRatioLevel,
            pc.metadata.positionType,
            pc.metadata.positionEntryPrice,
            pc.metadata.positionEntryTime,
            pc.positionClosingPrice,
            pc.positionClosingTime,
            pc.outcome,
            pc.net
        ])

    print(tabulate(table_data, headers=headers, tablefmt="simple_grid"))


def print_position_summary_table(closed_positions: List[PositionClose]) -> None:
    """Prints a summary table with profit/loss counts and total price."""

    num_profits = 0
    num_losses = 0
    total_net = 0

    for pc in closed_positions:
        if pc.outcome == 'PROFIT':
            num_profits += 1
        elif pc.outcome == 'LOSS':
            num_losses += 1
        total_net += pc.net  # Assuming you want to sum entry prices

    headers = ["Metric", "Value"]
    table_data = [
        ["Number of Profits", num_profits],
        ["Number of Losses", num_losses],
        ["Total Net Result", total_net]
    ]

    print(tabulate(table_data, headers=headers, tablefmt="simple_grid"))
