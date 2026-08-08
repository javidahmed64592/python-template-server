"""Template server router."""

from fastapi import Request

from python_template_server.models import GetConfigResponse, GetHealthResponse, TemplateServerConfig
from python_template_server.routers import BaseRouter


class TemplateServerRouter(BaseRouter):
    """Router for the template server."""

    def configure_router(self, config: TemplateServerConfig, version: str) -> None:
        """Configure the router with server configuration and version.

        :param TemplateServerConfig config: The server configuration
        :param str version: The server version
        """
        self.config = config
        self.version = version

    def setup_routes(self) -> None:
        """Set up the API routes for the template server."""
        self.add_route(
            endpoint="/health",
            handler_function=self.get_health,
            response_model=GetHealthResponse,
            methods=["GET"],
            limited=False,
        )
        self.add_route(
            endpoint="/config",
            handler_function=self.get_config,
            response_model=GetConfigResponse,
            methods=["GET"],
            limited=False,
        )

    async def get_health(self, request: Request) -> GetHealthResponse:
        """Get server health.

        :param Request request: The incoming HTTP request
        :return GetHealthResponse: Health status response
        """
        return GetHealthResponse(message="Server is healthy")

    async def get_config(self, request: Request) -> GetConfigResponse:
        """Get server configuration.

        :param Request request: The incoming HTTP request
        :return GetConfigResponse: Configuration response
        """
        return GetConfigResponse(
            message="Configuration retrieved successfully.",
            config=self.config,
            version=self.version,
        )
