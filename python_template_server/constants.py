"""Constants used across the server."""

from pyhere import here

# General constants
ROOT_DIR = here()
CONFIG_DIR_NAME = "configuration"
LOG_DIR_NAME = "logs"
CONFIG_DIR = ROOT_DIR / CONFIG_DIR_NAME
LOG_DIR = ROOT_DIR / LOG_DIR_NAME

CONFIG_FILE_NAME = "config.json"
LOG_FILE_NAME = "server.log"
ENV_FILE_NAME = ".env"

CONFIG_FILE_PATH = CONFIG_DIR / CONFIG_FILE_NAME
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME
ENV_FILE_PATH = ROOT_DIR / ENV_FILE_NAME

BYTES_TO_MB = 1024 * 1024

# Main constants
PACKAGE_NAME = "python-template-server"
API_PREFIX = "/api"
API_KEY_HEADER_NAME = "X-API-Key"

# Authentication constants
ENV_VAR_NAME = "API_TOKEN_HASH"
TOKEN_LENGTH = 32

# Logging constants
LOG_MAX_BYTES = 10 * BYTES_TO_MB  # 10 MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(module)s]: %(message)s"
LOG_DATE_FORMAT = "%d/%m/%Y | %H:%M:%S"
LOG_LEVEL = "INFO"
