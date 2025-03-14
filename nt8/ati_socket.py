import datetime
import socket
import threading
from nt8.enums import MarketDataType, Message
from utilities.logger import config_logging

logger = config_logging(__name__)


class AtiSocket:

    def __init__(
        self,
        sock,
        commandHandler,
        confirmOrdersHandler,
        dataHandler,
        subscribeHandler,
        valueHandler,
    ):
        self.commandHandler = commandHandler
        self.confirmOrdersHandler = confirmOrdersHandler
        self.dataHandler = dataHandler
        self.subscribeHandler = subscribeHandler
        self.valueHandler = valueHandler
        self.socket = sock
        self.lock = threading.Lock()
        self.buffer = bytearray()
        self.thread = threading.Thread(
            target=self.loop, name="NT AtiSocket", daemon=True
        )
        self.thread.start()
        logger.info("AtiSocket thread started.")

    @property
    def is_connected(self):
        return self.socket is not None

    def Dispose(self):
        with self.lock:
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.socket.close()
                self.socket = None

    def loop(self):
        # with self.lock:
        try:
            while True:
                # sleep(2)
                # msg_type = self.ReadInteger()
                msg_type = self.read_integer()
                # print(f"Received message type: {msg_type}")
                if msg_type == Message.COMMAND.value:
                    obj2 = self.read_string()
                    if self.commandHandler:
                        self.commandHandler(obj2)
                elif msg_type == Message.CONFIRMORDERS.value:
                    obj = self.read_integer()
                    if self.confirmOrdersHandler:
                        self.confirmOrdersHandler(obj)
                elif msg_type == Message.DATA.value:
                    arg4 = MarketDataType(self.read_integer())
                    arg5 = self.read_string()
                    arg6 = self.read_double()
                    arg7 = self.read_integer()
                    arg8 = datetime.datetime(1800, 1, 1)
                    text = self.read_string()
                    if text:
                        try:
                            arg8 = datetime.datetime.strptime(text, "%Y%m%d%H%M%S")
                        except ValueError:
                            pass
                    if self.dataHandler:
                        self.dataHandler(arg5, arg4, arg6, arg7, arg8)
                elif msg_type == Message.SUBSCRIBE.value:
                    arg3 = self.read_string()
                    num = self.read_integer()
                    if self.subscribeHandler:
                        self.subscribeHandler(arg3, num != 0)
                elif msg_type == Message.VALUE.value:
                    arg = self.read_string()
                    arg2 = self.read_string()
                    if self.valueHandler:
                        self.valueHandler(arg, arg2)
        except Exception as e:
            logger.error(f"Exception in AtiSocket Loop: {e}")
            self.Dispose()

    def read_double(self):
        return float(self.read_string())

    def read_integer(self):
        return int(self.read_string())

    def read_string(self):
        while True:
            idx = self.buffer.find(b"\x00")
            if idx != -1:
                chunk = self.buffer[:idx]
                del self.buffer[: idx + 1]
                result = chunk.decode("ascii")
                # print(f"ReadString: {result}")
                return result
            else:
                try:
                    data = self.socket.recv(4096)
                    # print(f"Received data: {data}")
                except Exception as e:
                    logger.error(f"Exception in ReadString: {e}")
                    self.Dispose()
                    raise
                if not data:
                    logger.error("No data received, socket may be closed.")
                    self.Dispose()
                    raise Exception("Socket closed")
                self.buffer.extend(data)

    def send(self, val):
        if self.socket is None:
            return
        with self.lock:
            if isinstance(val, (int, float)):
                buf = str(val)
            else:
                buf = val
            data = buf.encode("ascii") + b"\x00"
            try:
                self.socket.sendall(data)
            except Exception:
                self.Dispose()
