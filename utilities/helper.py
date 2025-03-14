import os
import uuid
from typing import Tuple, Optional
import xml.etree.ElementTree as ET

from redis.cluster import RedisCluster
import redis

from utilities.decorators.cache.cache import Cache
from utilities.logger import config_logging

logger = config_logging(__name__)

TICK_TO_POINT = {"NQ": 4, "MNQ": 4, "ES": 4, "GC": 10, "MES": 4}

PROJ_ID = "Feb"
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = os.getenv("REDIS_PORT", 10000)
REDIS_PASSWORD = os.getenv(
    "REDIS_PASSWORD", ""
)
REDIS_NOTIFICATIONS_STREAM: str = os.getenv(
    "REDIS_NOTIFICATIONS_STREAM", "ORDERS_NOTIFICATIONS_STREAM"
)

def get_redis_client() -> Optional[RedisCluster]:
    try:
        r = RedisCluster(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
            ssl=True,
        )
        r.ping()
        logger.warning(
            f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT} successfully!"
        )
        return r
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def save_xml(xml_data, file_name, strategy_dict_path: str):
    with open(f"{strategy_dict_path}/{file_name}.xml", "w") as file:
        file.write(xml_data)
    logger.info(f"XML data saved to {file_name}")


def create_xml(
    TP: int,
    SL: int,
    instrument_name: str,
) -> Tuple[str, str]:

    calculate = "OnBarClose"

    calculation_mode = "Ticks"
    time_in_force = "Gtc"
    atm_selector = uuid.uuid4().hex
    quantity = 1
    stop_loss = 0
    target = 0
    name = None
    # for instrument in Instruments:
    #     if instrument_name in instrument.value:
    #         name = instrument_name.split(" ")[0]
    #         target = TP * TICK_TO_POINT[name]
    #         stop_loss = SL * TICK_TO_POINT[name]
    #         break

    name = instrument_name.split(" ")[0]
    target = TP * TICK_TO_POINT[name]
    stop_loss = SL * TICK_TO_POINT[name]

    strategy_name = f"{PROJ_ID}_{TP}TP_{SL}SL_{name}"
    # Create the root element
    root = ET.Element("NinjaTrader")
    # Create the AtmStrategy element
    atm_strategy = ET.SubElement(
        root,
        "AtmStrategy",
        {
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )

    # Static elements from the template
    ET.SubElement(atm_strategy, "IsVisible").text = "true"
    ET.SubElement(atm_strategy, "AreLinesConfigurable").text = "true"
    ET.SubElement(atm_strategy, "ArePlotsConfigurable").text = "true"
    ET.SubElement(atm_strategy, "BarsToLoad").text = "0"
    ET.SubElement(atm_strategy, "DisplayInDataBox").text = "true"
    ET.SubElement(atm_strategy, "From").text = "2099-12-01T00:00:00"
    ET.SubElement(atm_strategy, "Panel").text = "0"
    ET.SubElement(atm_strategy, "ScaleJustification").text = "Right"
    ET.SubElement(atm_strategy, "ShowTransparentPlotsInDataBox").text = "false"
    ET.SubElement(atm_strategy, "To").text = "1800-01-01T00:00:00"

    # Dynamic elements from function parameters
    ET.SubElement(atm_strategy, "Calculate").text = calculate
    ET.SubElement(atm_strategy, "Template").text = strategy_name
    ET.SubElement(atm_strategy, "TimeInForce").text = time_in_force
    ET.SubElement(atm_strategy, "AtmSelector").text = atm_selector

    # Static elements continued
    ET.SubElement(atm_strategy, "Displacement").text = "0"
    ET.SubElement(atm_strategy, "IsAutoScale").text = "true"
    ET.SubElement(atm_strategy, "IsDataSeriesRequired").text = "false"
    ET.SubElement(atm_strategy, "IsOverlay").text = "false"
    ET.SubElement(atm_strategy, "Lines")
    ET.SubElement(atm_strategy, "MaximumBarsLookBack").text = "TwoHundredFiftySix"
    ET.SubElement(atm_strategy, "Name").text = "AtmStrategy"
    ET.SubElement(atm_strategy, "Plots")
    ET.SubElement(atm_strategy, "SelectedValueSeries").text = "0"
    ET.SubElement(atm_strategy, "BarsRequiredToTrade").text = "0"
    ET.SubElement(atm_strategy, "Category").text = "Atm"
    ET.SubElement(atm_strategy, "ConnectionLossHandling").text = "KeepRunning"
    ET.SubElement(atm_strategy, "DaysToLoad").text = "1"
    ET.SubElement(atm_strategy, "DefaultQuantity").text = str(quantity)
    ET.SubElement(atm_strategy, "DisconnectDelaySeconds").text = "0"
    ET.SubElement(atm_strategy, "EntriesPerDirection").text = "1"
    ET.SubElement(atm_strategy, "EntryHandling").text = "AllEntries"
    ET.SubElement(atm_strategy, "ExitOnSessionCloseSeconds").text = "0"
    ET.SubElement(atm_strategy, "IncludeCommission").text = "false"
    ET.SubElement(atm_strategy, "IsAggregated").text = "false"
    ET.SubElement(atm_strategy, "IsExitOnSessionCloseStrategy").text = "false"
    ET.SubElement(atm_strategy, "IsFillLimitOnTouch").text = "false"
    ET.SubElement(atm_strategy, "IsOptimizeDataSeries").text = "false"
    ET.SubElement(atm_strategy, "IsStableSession").text = "false"
    ET.SubElement(atm_strategy, "IsTickReplay").text = "false"
    ET.SubElement(atm_strategy, "IsTradingHoursBreakLineVisible").text = "false"
    ET.SubElement(atm_strategy, "IsWaitUntilFlat").text = "false"
    ET.SubElement(atm_strategy, "NumberRestartAttempts").text = "0"
    ET.SubElement(atm_strategy, "OptimizationPeriod").text = "10"
    ET.SubElement(atm_strategy, "OrderFillResolution").text = "High"
    ET.SubElement(atm_strategy, "OrderFillResolutionType").text = "Tick"
    ET.SubElement(atm_strategy, "OrderFillResolutionValue").text = "1"
    ET.SubElement(atm_strategy, "RestartsWithinMinutes").text = "0"
    ET.SubElement(atm_strategy, "SetOrderQuantity").text = "Strategy"
    ET.SubElement(atm_strategy, "Slippage").text = "0"
    ET.SubElement(atm_strategy, "StartBehavior").text = "AdoptAccountPosition"
    ET.SubElement(atm_strategy, "StopTargetHandling").text = "PerEntryExecution"
    ET.SubElement(atm_strategy, "SupportsOptimizationGraph").text = "false"
    ET.SubElement(atm_strategy, "TestPeriod").text = "28"
    ET.SubElement(atm_strategy, "TradingHoursSerializable")
    ET.SubElement(atm_strategy, "Gtd").text = "1800-01-01T00:00:00"
    ET.SubElement(atm_strategy, "OnBehalfOf")
    ET.SubElement(atm_strategy, "ReverseAtStopStrategyId").text = "-1"
    ET.SubElement(atm_strategy, "ReverseAtTargetStrategyId").text = "-1"
    ET.SubElement(atm_strategy, "ShadowStrategyStrategyId").text = "-1"
    ET.SubElement(atm_strategy, "ShadowTemplate")

    # Brackets
    brackets = ET.SubElement(atm_strategy, "Brackets")
    bracket = ET.SubElement(brackets, "Bracket")
    ET.SubElement(bracket, "Quantity").text = str(quantity)
    ET.SubElement(bracket, "StopLoss").text = str(stop_loss)
    ET.SubElement(bracket, "Target").text = str(target)

    # Remaining fields
    ET.SubElement(atm_strategy, "CalculationMode").text = calculation_mode
    ET.SubElement(atm_strategy, "ChaseLimit").text = "0"
    ET.SubElement(atm_strategy, "EntryQuantity").text = str(quantity)
    ET.SubElement(atm_strategy, "InitialTickSize").text = "0"
    ET.SubElement(atm_strategy, "IsChase").text = "false"
    ET.SubElement(atm_strategy, "IsChaseIfTouched").text = "false"
    ET.SubElement(atm_strategy, "IsTargetChase").text = "false"
    ET.SubElement(atm_strategy, "ReverseAtStop").text = "false"
    ET.SubElement(atm_strategy, "ReverseAtTarget").text = "false"
    ET.SubElement(atm_strategy, "UseMitForProfit").text = "false"
    ET.SubElement(atm_strategy, "UseStopLimitForStopLossOrders").text = "false"

    # Convert to a string
    xml_data = ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")

    # Prettify the XML
    import xml.dom.minidom as minidom

    pretty_xml = minidom.parseString(xml_data).toprettyxml(indent="  ")

    return pretty_xml, strategy_name


@Cache.to_memory
def generate_strategy(key: str, instrument_name: str):
    # TODO: check if the xml already exist
    strategy_dict_path = atm_strategy_validator()
    tp_values, sl_values = map(int, key.split("_"))
    strategy, strategy_name = create_xml(tp_values, sl_values, instrument_name)
    save_xml(strategy, strategy_name, strategy_dict_path)
    return strategy_name


def atm_strategy_validator() -> str:
    """
    Validates the existence of the ATM strategy folder for the current user.

    This function constructs a path to the 'AtmStrategy' directory based on the
    current user's name and checks if the directory exists. If the directory
    exists, it returns the path; otherwise, it raises a FileNotFoundError.

    Returns:
        str: The valid path to the 'AtmStrategy' directory.

    Raises:
        FileNotFoundError: If the 'AtmStrategy' directory does not exist.
    """
    # Get the current user's name
    user_name = os.getlogin()
    logger.info(f"The current user is: {user_name}")

    # Construct the path where the AtmStrategy must be
    path = rf"C:\Users\{user_name}\Documents\NinjaTrader 8\templates\AtmStrategy"

    # Validate the constructed path
    if os.path.exists(path):
        logger.debug(f"The path '{path}' is valid.")
        return path
    else:
        logger.error(f"The path '{path}' does not exist.")
        raise FileNotFoundError(f"The path '{path}' does not exist.")
