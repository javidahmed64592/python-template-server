"""Template server router with health and login endpoints."""

from fastapi import Request

from python_template_server.models import GetConfigResponse, GetHealthResponse, GetLoginResponse, TemplateServerConfig
from python_template_server.routers import BaseRouter


class TemplateServerRouter(BaseRouter):
    """Router for the template server with health and login endpoints."""

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
            authentication_required=False,
        )
        self.add_route(
            endpoint="/config",
            handler_function=self.get_config,
            response_model=GetConfigResponse,
            methods=["GET"],
            limited=False,
            authentication_required=False,
        )
        self.add_route(
            endpoint="/login",
            handler_function=self.get_login,
            response_model=GetLoginResponse,
            methods=["GET"],
            limited=True,
            authentication_required=True,
        )

    async def get_health(self, request: Request) -> GetHealthResponse:
        """Get server health.

        :param Request request: The incoming HTTP request
        :return GetHealthResponse: Health status response
        :raise HTTPException: If the server token is not configured
        """
        return GetHealthResponse(message="Server is healthy")

    async def get_config(self, request: Request) -> GetConfigResponse:
        """Get server configuration.

        :param Request request: The incoming HTTP request
        :return GetConfigResponse: Configuration response
        :raise HTTPException: If the server token is not configured
        """
        return GetConfigResponse(
            message="Configuration retrieved successfully.",
            config=self.config,
            version=self.version,
        )

    async def get_login(self, request: Request) -> GetLoginResponse:
        """Handle user login and return a success response.

        :param Request request: The incoming HTTP request
        :return GetLoginResponse: Login success response
        :raise HTTPException: If the server token is not configured
        """
        return GetLoginResponse(message="Login successful.")
