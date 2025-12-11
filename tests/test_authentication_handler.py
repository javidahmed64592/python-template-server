"""Unit tests for the python_template_server.authentication_handler module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from python_template_server.authentication_handler import (
    generate_new_token,
    generate_token,
    hash_token,
    load_hashed_token,
    save_hashed_token,
    verify_token,
)
from python_template_server.constants import ENV_FILE_PATH, ENV_VAR_NAME, TOKEN_LENGTH


@pytest.fixture
def mock_generate_token() -> Generator[MagicMock]:
    """Mock the generate_token function."""
    with patch("python_template_server.authentication_handler.generate_token") as mock_generate:
        yield mock_generate


@pytest.fixture
def mock_hash_token() -> Generator[MagicMock]:
    """Mock the hash_token function."""
    with patch("python_template_server.authentication_handler.hash_token") as mock_hash:
        yield mock_hash


@pytest.fixture
def mock_saved_hashed_token() -> Generator[MagicMock]:
    """Mock the save_hashed_token function."""
    with patch("python_template_server.authentication_handler.save_hashed_token") as mock_save:
        yield mock_save


class TestAuthenticationHandler:
    """Unit tests for the authentication handler functions."""

    def test_generate_token(self) -> None:
        """Test the generate_token function."""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) == pytest.approx(TOKEN_LENGTH * 4 / 3, rel=1)

    def test_hash_token(self) -> None:
        """Test the hash_token function."""
        hashed = hash_token("testtoken")
        assert isinstance(hashed, str)
        expected_length = 64  # SHA-256 produces a 64-character hex string
        assert len(hashed) == expected_length

    def test_save_hashed_token(
        self, mock_hash_token: MagicMock, mock_exists: MagicMock, mock_set_key: MagicMock
    ) -> None:
        """Test the save_hashed_token function."""
        mock_exists.return_value = True
        save_hashed_token("testtoken")
        mock_set_key.assert_called_once_with(ENV_FILE_PATH, ENV_VAR_NAME, mock_hash_token.return_value)

    def test_save_hashed_token_file_creation(
        self, mock_hash_token: MagicMock, mock_exists: MagicMock, mock_touch: MagicMock, mock_set_key: MagicMock
    ) -> None:
        """Test the save_hashed_token function creates the .env file if it does not exist."""
        mock_exists.return_value = False
        save_hashed_token("testtoken")
        mock_touch.assert_called_once()
        mock_set_key.assert_called_once_with(ENV_FILE_PATH, ENV_VAR_NAME, mock_hash_token.return_value)

    @pytest.mark.parametrize(
        ("token", "expected"),
        [("token", "token"), (None, None)],
    )
    def test_load_hashed_token(self, mock_os_getenv: MagicMock, token: str, expected: str) -> None:
        """Test the load_hashed_token function."""
        mock_os_getenv.return_value = token
        result = load_hashed_token()
        assert result == expected

    @pytest.mark.parametrize(
        ("input_token", "stored_hash", "expected"),
        [
            ("validtoken", hash_token("validtoken"), True),
            ("invalidtoken", hash_token("othertoken"), False),
        ],
    )
    def test_verify_token(
        self,
        input_token: str,
        stored_hash: str,
        expected: bool,  # noqa: FBT001
    ) -> None:
        """Test the verify_token function."""
        result = verify_token(input_token, stored_hash)
        assert result == expected

    def test_verify_token_no_stored_hash(self) -> None:
        """Test the verify_token function when no stored hash is provided."""
        with pytest.raises(ValueError, match=r"No stored token hash found for verification."):
            verify_token("sometoken", "")

    def test_generate_new_token(
        self,
        mock_generate_token: MagicMock,
        mock_saved_hashed_token: MagicMock,
    ) -> None:
        """Test the generate_new_token function."""
        generate_new_token()
        mock_generate_token.assert_called_once()
        mock_saved_hashed_token.assert_called_once_with(mock_generate_token.return_value)
