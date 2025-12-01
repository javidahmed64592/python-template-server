"""FastAPI template server using uvicorn."""

from pathlib import Path
from typing import Any

from python_template_server.constants import CONFIG_FILE_PATH
from python_template_server.models import TemplateServerConfig
from python_template_server.template_server import TemplateServer


class ExampleServer(TemplateServer):
    """Example server inheriting from TemplateServer."""

    def __init__(self, config_filepath: Path = CONFIG_FILE_PATH) -> None:
        """Initialize the ExampleServer by delegating to the template server.

        :param Path config_filepath: Configuration filepath
        """
        super().__init__(config_filepath=config_filepath)

    def validate_config(self, config_data: dict[str, Any]) -> TemplateServerConfig:
        """Validate configuration from the config.json file.

        :return TemplateServerConfig: Loaded configuration
        """
        return super().validate_config(config_data)

    def setup_routes(self) -> None:
        """Set up API routes."""
        super().setup_routes()


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    server = ExampleServer()
    server.run()
