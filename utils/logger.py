"""
Centralized logging configuration for Monsterrr.
"""

import logging
import sys

# Example JSON log format setup
def setup_logger():
    logger = logging.getLogger("monsterrr")
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
