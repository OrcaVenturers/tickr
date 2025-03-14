import uuid
from datetime import datetime
import time
from enum import Enum

from nt8.client import NTClient
from nt8.enums import OrderTypes, OrcaOrderStatus, ActionTypes
from utilities.logger import config_logging

logger = config_logging(__name__)


class OrcaCommand(Enum):
    Place = "Place"
    Cancel = "Cancel"
    Change = "Change"
    ClosePosition = "ClosePosition"
    CloseStrategy = "CloseStrategy"


class Order:
    def __init__(
        self,
        instrument_name: str,
        action: ActionTypes,
        strategy: str,
        quantity: int,
        price: float,
        id_generator=True,
    ):
        self.price = price
        self.instrument_name = instrument_name
        self.id_generator = id_generator
        self.type = "NA"
        self.quantity = quantity

        self.action = action
        self.strategy = strategy

        self.created_date = datetime.now()

        self.status = OrcaOrderStatus.PENDING
        # used for order id.
        self.count = 0  # this is used to generate a unique order id for each time we place an order
        self.order_identifier = uuid.uuid4().hex[:8]

        # the bracket order ids
        self.stop_limit_id = None
        self.take_profit_id = None

        self.stop_limit_price = None
        self.take_profit_price = None

        self.exit_modify = False
        # TODO: given the first condition, maybe we don't need this
        self.break_even_mode = False

        # action of the order can change to buy or sell based on the Mode (Hybrid)
        self.current_action = None
        self.original_id = None
        self.id = None
        # TODO: NOW it is fixed, it is related to Exit strategy
        # first time only increased by 2x then 1x
        self.trailing_point = self.price
        self.trailing_point_mark_price_profit = self.price
        self.trailing_point_mark_price_lost = self.price

    def _generate_order_id(self, account_name) -> None:
        # everytime we place an order we generate a new order id
        self.count += 1
        self.id = f"ORCA_Q{self.quantity}_{account_name}__{self.instrument_name}_{self.type}_{self.order_identifier}_{self.count}"
        self.oco_id = f"OCO_{self.id}"

    def place(
        self,
        ninja_trader_client: NTClient,
        account_name: str,
        order_validately: str = "GTC",
        refresh: bool = False,
    ):

        if self.id_generator:
            self._generate_order_id(account_name)
            self.original_id = self.id

        self.current_action = self.action

        last_price = ninja_trader_client.get_last_price(self.instrument_name)

        # Determine order type based on action and price comparison
        if self.action not in (ActionTypes.BUY.value, ActionTypes.SELL.value):
            raise ValueError(f"Invalid action: {self.action}")

        order_type = (
            OrderTypes.STOP_MARKET.value
            if (self.action == ActionTypes.BUY.value and self.price < last_price)
            or (self.action == ActionTypes.SELL.value and self.price < last_price)
            else OrderTypes.MIT.value
        )
        #
        # # Update MIT flag based on order type
        # mit = order_type == OrderTypes.MIT.value
        #
        # # Set stop and limit prices based on order type
        # stop_price = self.price if not mit else 0
        # limit_price = 0 if not mit else self.price
        #
        # Set stop and limit prices based on order type
        stop_price = self.price
        limit_price = self.price

        if refresh:
            self._generate_order_id(account_name)

        # Place the order using the client
        ninja_trader_client.command(
            command=OrcaCommand.Place.value,
            account=account_name,
            instrument=self.instrument_name,
            order_id=self.id,
            limit_price=limit_price,
            stop_price=stop_price,
            action=self.action,
            quantity=self.quantity,
            order_type=order_type,
            time_in_force=order_validately,
            oco=self.oco_id,
            tpl=self.strategy,
            strategy="",
        )

        # TODO: not ready/ need testing
        #  we need to factor the instrament,
        #  so we know exaclty how to modify tp/sl price
        # if tp_distance and sl_distance:
        #     if action=='Buy':
        #         self.stop_limit_price -=sl_distance
        #         self.take_profit_price +=tp_distance
        #     else:
        #         self.stop_limit_price += sl_distance
        #         self.take_profit_price -= tp_distance

        self.status = OrcaOrderStatus.PLACED
        logger.info(
            f"Order placed {account_name}-{self.instrument_name}-{self.action}-{self.quantity}"
        )

    def cancel(
        self,
        ninja_trader_client: NTClient,
        account_name: str,
    ):
        ninja_trader_client.command(
            OrcaCommand.Cancel.value,
            account_name,
            self.instrument_name,
            self.id,
            0,
            "",
            0,
            0,
            "GTC",
            "",
            "",
            "",
            "",
        )
        logger.info(f"* Order {self.id} is Cancelled ********************")
        time.sleep(0.1)
        ninja_trader_client.command(
            OrcaCommand.Cancel.value,
            account_name,
            self.instrument_name,
            self.id,
            0,
            "",
            0,
            0,
            "GTC",
            "",
            "",
            "",
            "",
        )
        logger.info(f"* Order {self.id} is Cancelled ********************")

    def __repr__(self) -> str:
        return f"{self.type}-{self.price}-{self.id}-{self.count}"

    def __str__(self) -> str:
        return f"{self.type}-{self.price}-{self.id}-{self.count}"
