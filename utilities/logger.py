import logging
import os
import sys


# Log record format
LOG_RECORD = (
    "%(asctime)s|%(levelname)s|%(processName)s/%(process)d|%(threadName)s/%(thread)d|"
    "  %(name)s.%(funcName)s:%(lineno)d|%(message)s"
)


def config_logging(logger_name, level=logging.DEBUG):
    class MinLevelFilter(logging.Filter):
        """
        Logging filter class to filter out all records that have a level less than min_level
        """

        def __init__(self, min_level, max_level):
            super(MinLevelFilter, self).__init__()
            self.min_level = min_level
            self.max_level = max_level

        def filter(self, record):
            """
            Should we keep this record?
            :param record: logging record to be processed
            :return: True if yes False if no
            """
            return self.min_level <= record.levelno <= self.max_level

    handler_format = logging.Formatter(LOG_RECORD)

    h1 = logging.StreamHandler(sys.stdout)
    f1 = MinLevelFilter(logging.DEBUG, logging.WARNING)
    h1.addFilter(f1)
    h1.setFormatter(handler_format)

    h2 = logging.StreamHandler(sys.stderr)
    f2 = MinLevelFilter(logging.ERROR, logging.CRITICAL)
    h2.addFilter(f2)
    h2.setFormatter(handler_format)

    logger = logging.getLogger(logger_name)
    level = os.environ.get("LOGLEVEL", "DEBUG").upper()
    logger.setLevel(level)
    logger.root.handlers = [h1, h2]

    return logger
