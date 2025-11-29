"""FastAPI template server using uvicorn."""

from python_template_server.config import load_config, parse_args
from python_template_server.template_server import TemplateServer


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    args = parse_args()
    config = load_config(args.config_file)
    server = TemplateServer(config)
    server.run()
