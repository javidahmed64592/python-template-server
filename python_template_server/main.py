"""FastAPI template server using uvicorn."""

from python_template_server.models import TemplateServerConfig
from python_template_server.template_server import TemplateServer


class ExampleServer(TemplateServer):
    """Example server inheriting from TemplateServer."""

    def __init__(self) -> None:
        """Initialize the ExampleServer by delegating to the template server.

        :param TemplateServerConfig config: Example server configuration
        """
        super().__init__()

    def load_config(self) -> TemplateServerConfig:
        """Load configuration from the config.json file.

        :return TemplateServerConfig: Loaded configuration
        """
        return super().load_config()

    def setup_routes(self) -> None:
        """Set up API routes."""
        super().setup_routes()


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    server = ExampleServer()
    server.run()
