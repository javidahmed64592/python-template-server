"""Unit tests for the python_template_server.logging_setup module."""

import logging
from unittest.mock import MagicMock

from python_template_server.logging_setup import setup_logging


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_setup_logging_creates_log_directory(self, mock_mkdir: MagicMock) -> None:
        """Test that setup_logging creates the log directory."""
        setup_logging()
        mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_setup_logging_configures_handlers(self) -> None:
        """Test that setup_logging configures both console and file handlers."""
        expected_handlers = ["StreamHandler", "RotatingFileHandler"]

        setup_logging()

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == len(expected_handlers)

        # Check handler types
        handler_types = [type(handler).__name__ for handler in root_logger.handlers]
        for expected_handler in expected_handlers:
            assert expected_handler in handler_types

    def test_setup_logging_handlers_have_formatters(self) -> None:
        """Test that all handlers have formatters configured."""
        setup_logging()

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            assert handler.formatter is not None
            assert handler.formatter._fmt is not None
            assert "[%(asctime)s]" in handler.formatter._fmt
