"""Authentication handler for the server."""

import hashlib
import logging
import os
import secrets

import dotenv

from python_template_server.constants import ENV_FILE_PATH, ENV_VAR_NAME, TOKEN_LENGTH

logger = logging.getLogger(__name__)


def generate_token() -> str:
    """Generate a secure random token.

    :return str: A URL-safe token string
    """
    return secrets.token_urlsafe(TOKEN_LENGTH)


def hash_token(token: str) -> str:
    """Hash a token string using SHA-256.

    :param str token: The plain text token to hash
    :return str: The hexadecimal representation of the hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def save_hashed_token(token: str) -> None:
    """Hash a token and save it to the .env file.

    :param str token: The plain text token to hash and save
    """
    hashed = hash_token(token)

    if not ENV_FILE_PATH.exists():
        ENV_FILE_PATH.touch()

    dotenv.set_key(ENV_FILE_PATH, ENV_VAR_NAME, hashed)


def load_hashed_token() -> str:
    """Load the hashed token from environment variable.

    :return str: The hashed token string, or an empty string if not found
    """
    dotenv.load_dotenv(ENV_FILE_PATH)
    return os.getenv(ENV_VAR_NAME, "")


def verify_token(token: str, hashed_token: str) -> bool:
    """Verify a token against the stored hash.

    :param str token: The plain text token to verify
    :param str hashed_token: The stored hashed token for comparison
    :return bool: True if the token matches the stored hash, False otherwise
    """
    if not hashed_token:
        msg = "No stored token hash found for verification."
        raise ValueError(msg)

    return hash_token(token) == hashed_token


def generate_new_token() -> None:
    """Generate a new token, hash it, and save the hash to the .env file.

    This function generates a new secure random token, hashes it using SHA-256,
    and saves the hashed token to the .env file for future verification.
    """
    new_token = generate_token()
    save_hashed_token(new_token)
    logger.info("New API token generated and saved.")
    print(f"Token: {new_token}")  # Prevent logging token to log file
