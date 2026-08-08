"""Template server router."""

from fastapi import Request

from python_template_server.models import (
    GetAuthEnabledResponse,
    GetConfigResponse,
    GetHealthResponse,
    TemplateServerConfig,
)
from python_template_server.routers import BaseRouter


class TemplateServerRouter(BaseRouter):
    """Router for the template server."""

    def configure_router(self, config: TemplateServerConfig, version: str, proxy_url: str) -> None:
        """Configure the router with server configuration and version.

        :param TemplateServerConfig config: The server configuration
        :param str version: The server version
        :param str proxy_url: The proxy URL
        """
        self.config = config
        self.version = version
        self.proxy_url = proxy_url

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
            limited=True,
        )
        self.add_route(
            endpoint="/auth_enabled",
            handler_function=self.get_auth_enabled,
            response_model=GetAuthEnabledResponse,
            methods=["GET"],
            limited=True,
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

    async def get_auth_enabled(self, request: Request) -> GetAuthEnabledResponse:
        """Get authentication enabled status.

        :param Request request: The incoming HTTP request
        :return GetAuthEnabledResponse: Authentication enabled status response
        """
        return GetAuthEnabledResponse(
            message="Authentication enabled status retrieved successfully.",
            auth_enabled=self.proxy_url is not None,
        )
