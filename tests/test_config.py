"""Unit tests for the python_template_server.config module."""

import json
import logging
from unittest.mock import MagicMock

import pytest

from python_template_server.config import load_config, setup_logging
from python_template_server.models import TemplateServerConfig


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


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_success(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
        mock_template_server_config: TemplateServerConfig,
    ) -> None:
        """Test successful loading of config."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = json.dumps(mock_template_server_config.model_dump())

        config = load_config()

        assert isinstance(config, TemplateServerConfig)
        assert config == mock_template_server_config
        mock_sys_exit.assert_not_called()

    def test_load_config_file_not_found(
        self,
        mock_exists: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config when the file does not exist."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            load_config()

        mock_sys_exit.assert_called_once_with(1)

    def test_load_config_invalid_json(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config with invalid JSON content."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = "invalid json"

        with pytest.raises(SystemExit):
            load_config()

        mock_sys_exit.assert_called_with(1)

    def test_load_config_os_error(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config that raises an OSError."""
        mock_exists.return_value = True
        mock_open_file.side_effect = OSError("File read error")

        with pytest.raises(SystemExit):
            load_config()

        mock_sys_exit.assert_called_with(1)

    def test_load_config_validation_error(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config that fails validation."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = json.dumps({"server": {"host": "localhost", "port": 999999}})

        with pytest.raises(SystemExit):
            load_config()

        mock_sys_exit.assert_called_once_with(1)
