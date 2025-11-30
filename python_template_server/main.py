"""FastAPI template server using uvicorn."""

from python_template_server.constants import CONFIG_FILE_NAME
from python_template_server.logging_setup import setup_logging
from python_template_server.models import TemplateServerConfig
from python_template_server.template_server import TemplateServer


class ExampleServer(TemplateServer):
    """Example server inheriting from TemplateServer."""

    def __init__(self) -> None:
        """Initialize the ExampleServer by delegating to the template server.

        :param TemplateServerConfig config: Example server configuration
        """
        super().__init__()

    def load_config(self, config_file: str = CONFIG_FILE_NAME) -> TemplateServerConfig:
        """Load configuration from the config.json file.

        :param str config_file: Configuration file name
        :return TemplateServerConfig: Loaded configuration
        """
        return super().load_config(config_file)

    def setup_routes(self) -> None:
        """Set up API routes."""
        super().setup_routes()


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    setup_logging()
    server = ExampleServer()
    server.run()
