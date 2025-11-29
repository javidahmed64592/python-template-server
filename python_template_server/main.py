"""FastAPI template server using uvicorn."""

from python_template_server.config import load_config, parse_args
from python_template_server.models import TemplateServerConfig
from python_template_server.template_server import TemplateServer


class ExampleServer(TemplateServer):
    """Example server inheriting from TemplateServer."""

    def __init__(self, config: TemplateServerConfig) -> None:
        """Initialize the ExampleServer by delegating to the template server.

        :param TemplateServerConfig config: Example server configuration
        """
        super().__init__(config)

    def setup_routes(self) -> None:
        """Set up API routes."""
        super().setup_routes()


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    args = parse_args()
    config = load_config(args.config_file)
    server = ExampleServer(config)
    server.run()
