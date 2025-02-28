from dotenv import load_dotenv
import sys

load_dotenv()

from loguru import logger as logging

logging.remove(0)
logging.add(sys.stderr, level="SUCCESS")
