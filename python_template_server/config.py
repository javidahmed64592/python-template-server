"""Configuration handling for the server."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from python_template_server.constants import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_DIR,
    LOG_FILE_PATH,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)


def setup_logging() -> None:
    """Configure logging with both console and rotating file handlers.

    Creates a logs directory if it doesn't exist and sets up:
    - Console handler for stdout
    - Rotating file handler with size-based rotation
    """
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(exist_ok=True)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


# Setup logging on module import
setup_logging()
