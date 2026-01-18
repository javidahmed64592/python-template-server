"""Template FastAPI server module."""

import argparse
import json
import logging
import sys
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import metadata
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_core import ValidationError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from python_template_server.authentication_handler import load_hashed_token, verify_token
from python_template_server.certificate_handler import CertificateHandler
from python_template_server.constants import API_KEY_HEADER_NAME, API_PREFIX, CONFIG_FILE_PATH, PACKAGE_NAME, STATIC_DIR
from python_template_server.logging_setup import setup_logging
from python_template_server.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from python_template_server.models import (
    CustomJSONResponse,
    GetHealthResponse,
    GetLoginResponse,
    ResponseCode,
    ServerHealthStatus,
    TemplateServerConfig,
)

setup_logging()
logger = logging.getLogger(__name__)
argparser = argparse.ArgumentParser(description="Template FastAPI Server")


class TemplateServer(ABC):
    """Template FastAPI server.

    This class provides a template for building FastAPI servers with common features
    such as request logging, security headers and rate limiting.

    Ensure you implement the `setup_routes` and `validate_config` methods in subclasses.
    """

    def __init__(
        self,
        package_name: str = PACKAGE_NAME,
        api_prefix: str = API_PREFIX,
        api_key_header_name: str = API_KEY_HEADER_NAME,
        config_filepath: Path = CONFIG_FILE_PATH,
        config: TemplateServerConfig | None = None,
        static_dir: Path = STATIC_DIR,
    ) -> None:
        """Initialize the TemplateServer.

        :param str package_name: The package name for metadata retrieval
        :param str api_prefix: The API prefix for the server
        :param str api_key_header_name: The API key header name
        :param Path config_filepath: Path to the configuration file
        :param TemplateServerConfig | None config: Optional pre-loaded configuration
        """
        self.package_name = package_name
        self.api_prefix = api_prefix
        self.api_key_header_name = api_key_header_name
        self.config_filepath = config_filepath
        self.config = config or self.load_config(self.config_filepath)
        self.cert_handler = CertificateHandler(self.config.certificate)
        self.static_dir = static_dir

        CustomJSONResponse.configure(self.config.json_response)

        self.package_metadata = metadata(self.package_name)
        self.app = FastAPI(
            title=self.package_metadata["Name"],
            description=self.package_metadata["Summary"],
            version=self.package_metadata["Version"],
            root_path=self.api_prefix,
            lifespan=self.lifespan,
            default_response_class=CustomJSONResponse,
        )
        self.api_key_header = APIKeyHeader(name=self.api_key_header_name, auto_error=False)

        self.hashed_token = load_hashed_token()
        self._setup_request_logging()
        self._setup_security_headers()
        self._setup_cors()
        self._setup_rate_limiting()
        self.setup_routes()

    @property
    def static_dir_exists(self) -> bool:
        """Check if the static directory exists.

        :return bool: True if the static directory exists, False otherwise
        """
        return self.static_dir.exists()

    @staticmethod
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Handle application lifespan events."""
        yield

    @abstractmethod
    def validate_config(self, config_data: dict[str, Any]) -> TemplateServerConfig:
        """Validate configuration data against the TemplateServerConfig model.

        :param dict config_data: The configuration data to validate
        :return TemplateServerConfig: The validated configuration model
        :raise ValidationError: If the configuration data is invalid
        """
        return TemplateServerConfig.model_validate(config_data)

    def load_config(self, config_filepath: Path) -> TemplateServerConfig:
        """Load configuration from the specified json file.

        :param Path config_filepath: Path to the configuration file
        :return TemplateServerConfig: The validated configuration model
        :raise SystemExit: If configuration file is missing, invalid JSON, or fails validation
        """
        if not config_filepath.exists():
            logger.error("Configuration file not found: %s", config_filepath)
            sys.exit(1)

        try:
            with config_filepath.open() as f:
                config_data = json.load(f)
            config = self.validate_config(config_data)
            argparser.add_argument("--port", type=int, default=config.server.port, help="Port to run the server on")
            args = argparser.parse_args()
            config.server.port = args.port
            config.save_to_file(config_filepath)
        except json.JSONDecodeError:
            logger.exception("JSON parsing error: %s", config_filepath)
            sys.exit(1)
        except OSError:
            logger.exception("JSON read error: %s", config_filepath)
            sys.exit(1)
        except ValidationError:
            logger.exception("Invalid configuration in: %s", config_filepath)
            sys.exit(1)
        else:
            return config

    async def _verify_api_key(
        self, api_key: str | None = Security(APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False))
    ) -> None:
        """Verify the API key from the request header.

        :param str | None api_key: The API key from the X-API-Key header
        :raise HTTPException: If the API key is missing or invalid
        """
        if api_key is None:
            logger.warning("Missing API key in request!")
            raise HTTPException(
                status_code=ResponseCode.UNAUTHORIZED,
                detail="Missing API key",
            )

        try:
            if not verify_token(api_key, self.hashed_token):
                logger.warning("Invalid API key attempt!")
                raise HTTPException(
                    status_code=ResponseCode.UNAUTHORIZED,
                    detail="Invalid API key",
                )
            logger.debug("API key validated successfully.")
        except ValueError as e:
            logger.exception("Error verifying API key!")
            raise HTTPException(
                status_code=ResponseCode.UNAUTHORIZED,
                detail=str(e),
            ) from e

    def _setup_request_logging(self) -> None:
        """Set up request logging middleware."""
        self.app.add_middleware(RequestLoggingMiddleware)
        logger.info("Request logging enabled")

    def _setup_security_headers(self) -> None:
        """Set up security headers middleware."""
        self.app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_max_age=self.config.security.hsts_max_age,
            csp=self.config.security.content_security_policy,
        )

        logger.info(
            "Security headers enabled: HSTS max-age=%s, CSP=%s",
            self.config.security.hsts_max_age,
            self.config.security.content_security_policy,
        )

    def _setup_cors(self) -> None:
        """Set up CORS middleware."""
        if not self.config.cors.enabled:
            logger.info("CORS is disabled")
            return

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors.allow_origins,
            allow_credentials=self.config.cors.allow_credentials,
            allow_methods=self.config.cors.allow_methods,
            allow_headers=self.config.cors.allow_headers,
            expose_headers=self.config.cors.expose_headers,
            max_age=self.config.cors.max_age,
        )

        logger.info(
            "CORS enabled: origins=%s, credentials=%s, methods=%s, headers=%s",
            self.config.cors.allow_origins,
            self.config.cors.allow_credentials,
            self.config.cors.allow_methods,
            self.config.cors.allow_headers,
        )

    async def _rate_limit_exception_handler(self, request: Request, exc: RateLimitExceeded) -> CustomJSONResponse:
        """Handle rate limit exceeded exceptions.

        :param Request request: The incoming HTTP request
        :param RateLimitExceeded exc: The rate limit exceeded exception
        :return JSONResponse: HTTP 429 JSON response
        """
        logger.warning("Rate limit exceeded for %s", request.url.path)
        return CustomJSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(exc.retry_after)} if hasattr(exc, "retry_after") else {},
        )

    def _setup_rate_limiting(self) -> None:
        """Set up rate limiting middleware."""
        if not self.config.rate_limit.enabled:
            logger.info("Rate limiting is disabled")
            self.limiter = None
            return

        self.limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=self.config.rate_limit.storage_uri,
        )

        self.app.state.limiter = self.limiter
        self.app.add_exception_handler(RateLimitExceeded, self._rate_limit_exception_handler)  # type: ignore[arg-type]

        logger.info(
            "Rate limiting enabled: rate=%s, storage=%s",
            self.config.rate_limit.rate_limit,
            self.config.rate_limit.storage_uri or "in-memory",
        )

    def _limit_route(self, route_function: Callable[..., Any]) -> Callable[..., Any]:
        """Apply rate limiting to a route function if enabled.

        :param Callable route_function: The route handler function
        :return Callable: The potentially rate-limited route handler
        """
        if self.limiter is not None:
            return self.limiter.limit(self.config.rate_limit.rate_limit)(route_function)  # type: ignore[no-any-return]
        return route_function

    def run(self) -> None:
        """Run the server using uvicorn."""
        try:
            cert_file = self.config.certificate.ssl_cert_file_path
            key_file = self.config.certificate.ssl_key_file_path

            if not (cert_file.exists() and key_file.exists()):
                logger.warning("SSL certificate or key file not found, generating self-signed certificate...")
                self.cert_handler.generate_self_signed_cert()

            logger.info("Starting server: %s%s", self.config.server.url, self.api_prefix)
            uvicorn.run(
                self.app,
                host=self.config.server.host,
                port=self.config.server.port,
                ssl_keyfile=str(key_file),
                ssl_certfile=str(cert_file),
                log_level="warning",
                access_log=False,
            )
            logger.info("Server stopped.")
        except Exception:
            logger.exception("Failed to start!")
            sys.exit(1)

    def add_unauthenticated_route(
        self,
        endpoint: str,
        handler_function: Callable,
        response_model: type[BaseModel] | None,
        methods: list[str],
        limited: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Add an unauthenticated API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        :param bool limited: Whether to apply rate limiting to this route
        """
        self.app.add_api_route(
            endpoint,
            self._limit_route(handler_function) if limited else handler_function,
            methods=methods,
            response_model=response_model,
        )

    def add_authenticated_route(
        self,
        endpoint: str,
        handler_function: Callable,
        response_model: type[BaseModel],
        methods: list[str],
        limited: bool = True,  # noqa: FBT001, FBT002
    ) -> None:
        """Add an authenticated API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        :param bool limited: Whether to apply rate limiting to this route
        """
        self.app.add_api_route(
            endpoint,
            self._limit_route(handler_function) if limited else handler_function,
            methods=methods,
            response_model=response_model,
            dependencies=[Security(self._verify_api_key)],
        )

    @abstractmethod
    def setup_routes(self) -> None:
        """Set up API routes.

        This method must be implemented by subclasses to define API endpoints.

        Examples:
        ```python
        self.add_unauthenticated_route("/unprotected-endpoint", self.unprotected_endpoint, PublicResponseModel, ["GET"])
        self.add_authenticated_route("/protected-endpoint", self.protected_endpoint, PrivateResponseModel, ["POST"])
        ```

        """
        self.add_unauthenticated_route("/health", self.get_health, GetHealthResponse, ["GET"], limited=False)
        self.add_authenticated_route("/login", self.get_login, GetLoginResponse, methods=["GET"])
        if self.static_dir_exists:
            self.app.mount("/", StaticFiles(directory=str(self.static_dir), html=True), name="static")

            @self.app.exception_handler(StarletteHTTPException)
            async def custom_404_handler(request: Request, exc: StarletteHTTPException) -> FileResponse:
                """Handle 404 errors by serving custom 404.html if available."""
                if exc.status_code == ResponseCode.NOT_FOUND and self.static_dir_exists:
                    not_found_page = self.static_dir / "404.html"
                    if not_found_page.is_file():
                        return FileResponse(not_found_page, status_code=ResponseCode.NOT_FOUND)
                raise exc

    async def get_health(self, request: Request) -> GetHealthResponse:
        """Get server health.

        :param Request request: The incoming HTTP request
        :return GetHealthResponse: Health status response
        """
        if not self.hashed_token:
            return GetHealthResponse(
                code=ResponseCode.INTERNAL_SERVER_ERROR,
                message="Server token is not configured",
                timestamp=GetHealthResponse.current_timestamp(),
                status=ServerHealthStatus.UNHEALTHY,
            )

        return GetHealthResponse(
            code=ResponseCode.OK,
            message="Server is healthy",
            timestamp=GetHealthResponse.current_timestamp(),
            status=ServerHealthStatus.HEALTHY,
        )

    async def get_login(self, request: Request) -> GetLoginResponse:
        """Handle user login and return a success response."""
        logger.info("User login successful.")
        return GetLoginResponse(
            code=ResponseCode.OK,
            message="Login successful.",
            timestamp=GetLoginResponse.current_timestamp(),
        )
