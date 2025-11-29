"""Constants used across the server."""

# General constants
BYTES_TO_MB = 1024 * 1024

# Main constants
PACKAGE_NAME = "python-template-server"
API_PREFIX = "/api"
API_KEY_HEADER_NAME = "X-API-Key"
CONFIG_FILE_NAME = "config.json"

# Authentication constants
ENV_FILE_NAME = ".env"
ENV_VAR_NAME = "API_TOKEN_HASH"
TOKEN_LENGTH = 32

# Logging constants
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "server.log"
LOG_MAX_BYTES = 10 * BYTES_TO_MB  # 10 MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "[%(asctime)s] (%(levelname)s) %(module)s: %(message)s"
LOG_DATE_FORMAT = "%d/%m/%Y | %H:%M:%S"
LOG_LEVEL = "INFO"
