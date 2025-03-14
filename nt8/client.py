import socket
import threading
import time
import uuid
from collections import defaultdict

from nt8.ati_socket import AtiSocket
from nt8.enums import MarketDataType
from utilities.logger import config_logging

logger = config_logging(__name__)

DefaultHost = "127.0.0.1"
DefaultPort = 36973


class NTClient:
    def __init__(self):
        self.had_error = False
        self.host = DefaultHost
        self.port = DefaultPort
        self.showedError = False
        self.socket = None
        self.timer = None
        self.values = defaultdict(str)
        self.lock = threading.Lock()

    def add_value(self, key, value):
        # print(f"AddValue called with key: {key}, value: {value}")
        with self.lock:
            self.values[key] = value

    def set_up(self, show_message=True):
        if not self.had_error:
            if self.socket is None or not self.socket.is_connected:
                return self.set_up_now(show_message)
            return 0
        return -1

    def set_up_now(self, show_message):

        try:
            # Existing connection code...
            logger.info("Attempting to connect to the server...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            logger.info(f"Connected to {self.host}:{self.port}")
            self.socket = AtiSocket(sock, None, None, None, None, self.add_value)

            # Wait for the "ATI" key to be set
            # Wait for the "ATI" key to be set
            for _ in range(1000):
                if self.get_string("ATI"):
                    # print("Received 'ATI' key from server.")
                    break
                threading.Event().wait(0.01)
            else:
                logger.info("Timeout waiting for 'ATI' key from server.")

        except Exception as ex:
            self.socket = None
            self.had_error = True
            if not self.showedError:
                self.showedError = True
                if show_message:
                    logger.error(
                        f"Unable to connect to server ({self.host}/{self.port}): {ex}"
                    )
            self.timer = threading.Timer(10.0, self.on_timer_elapsed)
            self.timer.start()
            return -1
        self.had_error = False
        self.showedError = False
        return 0

    def on_timer_elapsed(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.set_up_now(True)

    def Dispose(self) -> None:
        if self.socket:
            self.socket.Dispose()
            self.socket = None
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def filled(self, order_id: str) -> int:
        if self.set_up(True) == 0:
            return self.get_int(f"Filled|{order_id}")
        return 0

    def get_string(self, key):
        if self.set_up(True) != 0:
            return ""
        with self.lock:
            return self.values.get(key, "")

    def get_double(self, key):
        value = self.get_string(key)
        try:
            return float(value) if value else 0.0
        except ValueError:
            return 0.0

    def get_int(self, key):
        value = self.get_string(key)
        try:
            return int(value) if value else 0
        except ValueError:
            return 0

    def send_command(self, command, *args):
        if self.set_up(True) != 0:
            return -1
        self.socket.send(command)
        for arg in args:
            self.socket.send(arg)
        return 0

    def ask(self, instrument, price, size):
        return self.send_command(1, 0, instrument, price, size, "")

    def bid(self, instrument, price, size):
        return self.send_command(1, 1, instrument, price, size, "")

    def last(self, instrument, price, size):
        return self.send_command(1, 2, instrument, price, size, "")

    def subscribe_market_data(self, instrument):
        # Subscribe to market data if needed
        if self.get_last_price(instrument) == 0:
            logger.debug(f"Subscribe for {instrument}")
            return self.send_command(4, instrument, 1)
        else:
            logger.debug(f"Already subscribe for {instrument}")

    def unsubscribe_market_data(self, instrument):
        return self.send_command(4, instrument, 0)

    def command(
        self,
        command,
        account,
        instrument,
        order_id,
        oco="",
        action="",
        quantity=0,
        order_type="",
        limit_price=0,
        stop_price=0,
        time_in_force="",
        tpl="",
        strategy="",
    ):
        cmd_string = f"{command};{account};{instrument};{action};{quantity};{order_type};{limit_price};{stop_price};{time_in_force};{oco};{order_id};{tpl};{strategy}"
        return self.send_command(0, cmd_string)

    def confirm_orders(self, confirm):
        return self.send_command(3, confirm)

    def connected(self, show_message):
        if (
            self.set_up(show_message == 1) == 0
            and not self.showedError
            and self.socket
            and self.socket.is_connected
        ):
            if self.get_string("ATI") == "True":
                return 0
        return -1

    def market_data(self, instrument, type_):
        key = f"MarketData|{instrument}|{type_.value}"
        return self.get_double(key)

    def market_position(self, instrument_name, account_name):
        key = f"MarketPosition|{instrument_name}|{account_name}"
        return self.get_int(key)

    def new_order_id(self):
        return uuid.uuid4().hex.upper()

    def all_orders(self, account_name: str, key_word: str = ""):
        orders_str = self.get_string(f"Orders|{account_name}")
        orders = orders_str.split("|")
        if key_word:
            orders = [order for order in orders if key_word in order]
        return orders

    def order_status_o(self, order_id):
        return self.get_string(f"OrderStatus|{order_id}")

    def order_status(self, order_id: str) -> str:
        if self.set_up(show_message=True) == 0:
            return self.get_string("OrderStatus|" + order_id)
        return ""

    def open_orders(self, account_name):
        orders = self.all_orders(account_name)
        status_counts = defaultdict(int)
        for order_id in orders:
            status = self.order_status(order_id)
            status_counts[status] += 1
            logger.info(f"{order_id} - {status}")
        return dict(status_counts)

    def set_up_connection(self, host, port):
        self.host = host
        self.port = port
        return self.set_up(True)

    def get_last_price(self, instrument_name):
        return self.market_data(instrument_name, MarketDataType.Last)

    def target_orders(self, strategy_id: str):
        if self.set_up(True) == 0:
            return self.get_int(f"TargetOrders|{strategy_id}")
        return 0

    def get_orders(self, account_name: str, order_identifier: str):
        """
        Retrieve orders based on the specified criteria.
        - list: A list of order IDs based on the specified criteria.
        """

        orders = self.all_orders(account_name)

        # Find the index of the first order that contains the GroupIdentifier
        start_index = next(
            (i for i, order in enumerate(orders) if order_identifier in order), None
        )

        # Return orders starting from the found index, or an empty list if not found
        return orders[start_index:] if start_index is not None else []

        # TODO: maybe we don't nneed
        # # Retrieve only placed orders with a specific naming convention
        # return self.orders(account_name, 1000, f"{order_identifier}__ORCA_Q")

    def is_target_filled_oco_orders(self):
        """

        :param order_ids:
        :return:
        """
        pass
        # for order_id in order_ids:
        #     if "ORCA" not in order_id and self.filled(order_id) != 0:
        #         log.debug(f"Order with Id {order_id} has been filled.")
        #         return True
        # return False

    def buying_power(self, account_name: str):
        if self.set_up(show_message=True) == 0:
            return self.get_double(f"BuyingPower|{account_name}")
        return 0.0

    def cash_value(self, account_name: str):
        if self.set_up(show_message=True) == 0:
            return self.get_double(f"CashValue|{account_name}")
        return 0.0

    # Add other methods as needed, following the pattern above...
    #     ---------------
    def all_orders(self, account):
        if self.set_up(show_message=True) == 0:
            return self.get_string("Orders|" + account).split("|")
        # Return an empty list (Python equivalent of an empty string array)
        return []

    # TODO: Check1
    def orders(self, account_name, order_number=50, keyword=""):
        if self.set_up(show_message=True) == 0:
            if keyword == "":
                all_orders = self.get_string("Orders|" + account_name).split("|")
            else:
                all_orders = self.filter_orders(
                    self.get_string("Orders|" + account_name).split("|"), keyword
                )

            if 0 <= order_number <= len(all_orders):
                selected_orders = self.all_orders[:order_number]
                return selected_orders
            else:
                # Return all orders if order_number is out of range
                return all_orders
        # Return an empty list
        return []

    def all_orders_with_keyword(self, account_name, keyword=""):
        if self.set_up(show_message=True) == 0:
            if keyword == "":
                all_orders = self.get_string("Orders|" + account_name).split("|")
            else:
                all_orders = self.filter_orders(
                    self.get_string("Orders|" + account_name).split("|"), keyword
                )
            # Return all orders
            return all_orders
        # Return an empty list
        return []

    def filter_orders(self, all_orders, keyword):
        filtered_orders = [order for order in all_orders if keyword in order]
        return filtered_orders

    # ninjaTraderClinet.OrderStatus("wBtl384__ORCA_Q1_Playback101_NQ SEP24_BUY_9ADD14C4_G")
    # "Filled"
    # ninjaTraderClinet.Filled("wBtl384__ORCA_Q1_Playback101_NQ SEP24_BUY_9ADD14C4_G")
    # 1
    def order_status(self, order_id):
        if self.set_up(show_message=True) == 0:
            return self.get_string("OrderStatus|" + order_id)
        return ""

    # ninjaTraderClinet.OpenOrders("Playback101")
    # OrcaBot.NT8.NTClient: 2024-09-22 22:42:01,357 [13] INFO  OrcaBot.NT8.NTClient OpenOrders - aYEt656__ORCA_Q1_Playback101_NQ SEP24_BUY_7FE186DB_G - Filled
    # OrcaBot.NT8.NTClient: 2024-09-22 22:42:01,359 [13] INFO  OrcaBot.NT8.NTClient OpenOrders - 771d7c9802464a4fb97b3a7b40f57a26 - Accepted
    # OrcaBot.NT8.NTClient: 2024-09-22 22:42:01,360 [13] INFO  OrcaBot.NT8.NTClient OpenOrders - 201fd1d28cfa47b78ce29322db433c12 - Working
    # OrcaBot.NT8.NTClient: 2024-09-22 22:42:01,361 [13] INFO  OrcaBot.NT8.NTClient OpenOrders - aYEt656__ORCA_Q2_Playback101_NQ SEP24_SELL_0CAE671D_G - Accepted
    # ninjaTraderClinet.OpenOrders("Playback101")
    # OrcaBot.NT8.NTClient: 2024-09-22 22:55:00,237 [16] INFO  OrcaBot.NT8.NTClient OpenOrders - aYEt656__ORCA_Q1_Playback101_NQ SEP24_BUY_7FE186DB_G - Filled
    # OrcaBot.NT8.NTClient: 2024-09-22 22:55:00,239 [16] INFO  OrcaBot.NT8.NTClient OpenOrders - 771d7c9802464a4fb97b3a7b40f57a26 - Cancelled
    # OrcaBot.NT8.NTClient: 2024-09-22 22:55:00,240 [16] INFO  OrcaBot.NT8.NTClient OpenOrders - 201fd1d28cfa47b78ce29322db433c12 - Cancelled
    # OrcaBot.NT8.NTClient: 2024-09-22 22:55:00,241 [16] INFO  OrcaBot.NT8.NTClient OpenOrders - aYEt656__ORCA_Q2_Playback101_NQ SEP24_SELL_0CAE671D_G - Cancelled
    # Count = 2
    #     [0]: {[Filled, 1]}
    #     [1]: {[Cancelled, 3]}

    def open_orders(self, account_name):
        orders = ""
        if self.set_up(show_message=True) == 0:
            orders = self.get_string("Orders|" + account_name)

        substrings = orders.split("|")
        # Dictionary to store status counts
        active_order_no = {}

        for id in substrings:
            status = self.order_status(id)

            # Check if status is already in dictionary, if not add with count 1
            if status not in active_order_no:
                active_order_no[status] = 1
            else:
                active_order_no[status] += 1

            # Assuming there's some logging mechanism like log.info()
            logger.debug(f"{id} - {status}")

        return active_order_no

    # ninjaTraderClinet.OpenOrdersByInstrument("Playback101", "NQ SEP24")

    def get_orders_brackets_ids(self, account_name: str, key="ORCA", last_orders=2):
        """
        Retrieve the stop and profit order IDs
        """
        if self.set_up(show_message=True) == 0:
            _orders = self.get_string("Orders|" + account_name)

            return _orders.split("|")[-2:]
        return []

    def get_order_brackets_ids2(self, account_name: str, order_id: str, key="ORCA"):
        """
        Retrieve the stop and profit order ID for a given order ID.
        """
        order_brackets_ids = self.orders(account_name)
        return order_brackets_ids.get(order_id, {})

    def parsing_orders_ids(self, id_list, key="ORCA"):
        orders_dict = {}
        orders_dict[order_id] = {"sl": all_other_ids[i + 1], "tp": all_other_ids[i + 2]}

        return orders_dict

    def parsing_orders_ids_old(self, id_list, key="ORCA"):
        orders_id_dict = {}
        orders_dict = {}
        all_other_ids = []
        id_index = 0
        # Iterate over the list of strings
        for _id in id_list:
            if _id.startswith("Orca"):
                id_index += 1
                orders_id_dict[id_index] = _id
            else:
                all_other_ids.append(_id)

        for i, order_id_position in enumerate(orders_id_dict):
            # Create a tuple of the current item and the next item
            order_id = orders_id_dict[order_id_position]
            orders_dict[order_id] = {
                "sl": all_other_ids[i + 1],
                "tp": all_other_ids[i + 2],
            }

        return orders_dict

    def parsing_orders_ids_old(self, id_list, key="ORCA"):
        result = {}
        i = 0
        n = len(id_list)

        while i < n:
            current_id = id_list[i]

            # Check if the current ID starts with "Sim"
            if current_id.startswith(key):
                sim_id = current_id

                # Ensure we have enough elements left for stop and profile
                if (
                    i + 2 < n
                    and not id_list[i + 1].startswith(key)
                    and not id_list[i + 2].startswith(key)
                ):
                    stop = id_list[i + 1]
                    profile = id_list[i + 2]
                    result[sim_id] = {"sl_id": stop, "tp_id": profile}
                    i += 3  # Skip over Sim ID, stop, and profile
                else:
                    i += 1  # Skip just the current Sim ID if no valid stop/profile pair exists
            else:
                i += 1  # Move to the next ID if it's not a key ID

        return result

    def open_orders_by_instrument(self, account_name, instrument_name):
        orders = ""
        if self.set_up(show_message=True) == 0:
            orders = self.get_string("Orders|" + account_name)

        substrings = orders.split("|")
        active_order_count = 0

        for id in substrings:
            # Check order instrument (similar to StringComparison.OrdinalIgnoreCase in Python)
            # if instrument_name.lower() in id.lower():
            status = self.order_status(id)
            if status == "Cancelled":
                continue
            if status in ["Accepted", "Filled"]:
                active_order_count += 1 if self.filled(id) == 0 else 0

        return active_order_count

    # Placeholders for other functions used in the code
    # --------------------

    def flat_instrument(self, account_name: str, instrument_name: str):
        try:
            # Close all positions for the specified account and instrument.
            self.close_all_positions(account_name, instrument_name)
            time.sleep(0.5)
            self.close_all_positions(account_name, instrument_name)

            # Cancel all orders for the specified account (no instrument).
            self.cancel_all_orders(account_name)

            logger.info(f"Flatted: {account_name} {instrument_name}")
        except Exception as ex:
            logger.error(ex)

            # Close all positions for the specified account and instrument again.
            self.close_all_positions(account_name, instrument_name)

            # Cancel all orders for the specified account.
            self.cancel_all_orders(account_name)

            logger.info(f"Flatted second time: {account_name} {instrument_name}")

    def flat_accounts_instrument(self, account_names: list[str], instrument_name: str):
        for account_name in account_names:
            # Close all positions for the specified account and instrument.
            self.close_all_positions(account_name, instrument_name)

            # Cancel all orders for the specified account.
            self.cancel_all_orders(account_name)

    def close_all_positions(self, account_name: str, instrument_name: str):
        """
        Close all positions for a specified account and instrument.
        """
        self.command(
            "CLOSEPOSITION",
            account_name,
            instrument_name,
            "FLAT",
            0,
            "",
            0.0,
            0.0,
            "",
            "",
            "",
            "",
            "",
        )

    def cancel_all_instrument_orders(
        self,
        account_name: str,
        instrument_name: str,
        order_number: int = 50,
        keyword: str = "ORCA_",
    ):
        """
        Cancel all orders for a specific instrument and account, based on optional parameters.
        """
        # Retrieve all placed orders for the specified account and instrument.
        all_placed_orders = self.orders(account_name, 500)

        # Iterate through the list of orders and cancel each one asynchronously.
        for order_id in all_placed_orders:
            self.cancel_order_adv(account_name, instrument_name, order_id)

    def cancel_all_orders(self, account_name: str):
        """
        Cancel all orders for a specified account.
        """
        self.command(
            "CANCELALLORDERS",
            account_name,
            "",
            "",
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

    def cancel_order_adv(self, account_name: str, instrument_name: str, order_id: str):
        """
        Cancel a specific order for a specified account and instrument.
        """
        # Send the command to cancel the specified order.
        self.command(
            "CANCEL",
            account_name,
            instrument_name,
            "",
            0,
            "",
            0,
            0,
            "GTC",
            "",
            order_id,
            "",
            "",
        )
        logger.info(f"* Order {order_id} is Cancelled ********************")
        time.sleep(0.1)
        self.command(
            "CANCEL",
            account_name,
            instrument_name,
            "",
            0,
            "",
            0,
            0,
            "GTC",
            "",
            order_id,
            "",
            "",
        )
        logger.info(f"* Order {order_id} is Cancelled ********************")
