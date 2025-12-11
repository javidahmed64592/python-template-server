"""Template FastAPI server module."""

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
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from pydantic_core import ValidationError
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from python_template_server.authentication_handler import load_hashed_token, verify_token
from python_template_server.constants import API_KEY_HEADER_NAME, API_PREFIX, CONFIG_FILE_PATH, PACKAGE_NAME
from python_template_server.logging_setup import setup_logging
from python_template_server.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from python_template_server.models import (
    CustomJSONResponse,
    GetHealthResponse,
    ResponseCode,
    ServerHealthStatus,
    TemplateServerConfig,
)
from python_template_server.prometheus_handler import BaseMetricNames, PrometheusHandler

setup_logging()
logger = logging.getLogger(__name__)


class TemplateServer(ABC):
    """Template FastAPI server.

    This class provides a template for building FastAPI servers with common features
    such as request logging, security headers, rate limiting, and Prometheus metrics.

    Ensure you implement the `setup_routes` and `validate_config` methods in subclasses.
    """

    def __init__(
        self,
        package_name: str = PACKAGE_NAME,
        api_prefix: str = API_PREFIX,
        api_key_header_name: str = API_KEY_HEADER_NAME,
        config_filepath: Path = CONFIG_FILE_PATH,
        config: TemplateServerConfig | None = None,
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
        self.config = config or self.load_config(config_filepath)

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
        self._setup_rate_limiting()
        self._setup_metrics()
        self.setup_routes()

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

        config_data = {}
        try:
            with config_filepath.open() as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            logger.exception("JSON parsing error: %s", config_filepath)
            sys.exit(1)
        except OSError:
            logger.exception("JSON read error: %s", config_filepath)
            sys.exit(1)

        try:
            return self.validate_config(config_data)
        except ValidationError:
            logger.exception("Invalid configuration in: %s", config_filepath)
            sys.exit(1)

    async def _verify_api_key(
        self, api_key: str | None = Security(APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False))
    ) -> None:
        """Verify the API key from the request header.

        :param str | None api_key: The API key from the X-API-Key header
        :raise HTTPException: If the API key is missing or invalid
        """
        if api_key is None:
            logger.warning("Missing API key in request!")
            self.prometheus_handler.increment_counter(BaseMetricNames.AUTH_FAILURE_TOTAL, labels={"reason": "missing"})
            raise HTTPException(
                status_code=ResponseCode.UNAUTHORIZED,
                detail="Missing API key",
            )

        try:
            if not verify_token(api_key, self.hashed_token):
                logger.warning("Invalid API key attempt!")
                self.prometheus_handler.increment_counter(
                    BaseMetricNames.AUTH_FAILURE_TOTAL, labels={"reason": "invalid"}
                )
                raise HTTPException(
                    status_code=ResponseCode.UNAUTHORIZED,
                    detail="Invalid API key",
                )
            logger.debug("API key validated successfully.")
            self.prometheus_handler.increment_counter(BaseMetricNames.AUTH_SUCCESS_TOTAL)
        except ValueError as e:
            logger.exception("Error verifying API key!")
            self.prometheus_handler.increment_counter(BaseMetricNames.AUTH_FAILURE_TOTAL, labels={"reason": "error"})
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

    async def _rate_limit_exception_handler(self, request: Request, exc: RateLimitExceeded) -> CustomJSONResponse:
        """Handle rate limit exceeded exceptions and track metrics.

        :param Request request: The incoming HTTP request
        :param RateLimitExceeded exc: The rate limit exceeded exception
        :return JSONResponse: HTTP 429 JSON response
        """
        self.prometheus_handler.increment_counter(
            BaseMetricNames.RATE_LIMIT_EXCEEDED_TOTAL, labels={"endpoint": request.url.path}
        )

        # Return JSON response with 429 status
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

    def _setup_metrics(self) -> None:
        """Set up Prometheus metrics."""
        self.prometheus_handler = PrometheusHandler(self.app)
        self.prometheus_handler.set_gauge(BaseMetricNames.TOKEN_CONFIGURED, 1 if self.hashed_token else 0)
        logger.info("Prometheus metrics enabled.")

    def run(self) -> None:
        """Run the server using uvicorn.

        :raise FileNotFoundError: If SSL certificate files are missing
        """
        try:
            cert_file = self.config.certificate.ssl_cert_file_path
            key_file = self.config.certificate.ssl_key_file_path

            if not (cert_file.exists() and key_file.exists()):
                logger.error("SSL certificate files are missing. Expected: '%s' and '%s'", cert_file, key_file)
                sys.exit(1)

            logger.info("Starting server: %s%s", self.config.server.url, self.api_prefix)
            uvicorn.run(
                self.app,
                host=self.config.server.host,
                port=self.config.server.port,
                ssl_keyfile=str(key_file),
                ssl_certfile=str(cert_file),
            )
            logger.info("Server stopped.")
        except OSError:
            logger.exception("Failed to start - ran into an OSError!")
            sys.exit(1)

    def add_unauthenticated_route(
        self, endpoint: str, handler_function: Callable, response_model: type[BaseModel], methods: list[str]
    ) -> None:
        """Add an unauthenticated API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        """
        self.app.add_api_route(
            endpoint,
            self._limit_route(handler_function),
            methods=methods,
            response_model=response_model,
        )

    def add_authenticated_route(
        self, endpoint: str, handler_function: Callable, response_model: type[BaseModel], methods: list[str]
    ) -> None:
        """Add an authenticated API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        """
        self.app.add_api_route(
            endpoint,
            self._limit_route(handler_function),
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
        self.add_unauthenticated_route("/health", self.get_health, GetHealthResponse, ["GET"])

    async def get_health(self, request: Request) -> GetHealthResponse:
        """Get server health.

        :param Request request: The incoming HTTP request
        :return GetHealthResponse: Health status response
        """
        if not self.hashed_token:
            self.prometheus_handler.set_gauge(BaseMetricNames.TOKEN_CONFIGURED, 0)
            return GetHealthResponse(
                code=ResponseCode.INTERNAL_SERVER_ERROR,
                message="Server token is not configured",
                timestamp=GetHealthResponse.current_timestamp(),
                status=ServerHealthStatus.UNHEALTHY,
            )

        self.prometheus_handler.set_gauge(BaseMetricNames.TOKEN_CONFIGURED, 1)
        return GetHealthResponse(
            code=ResponseCode.OK,
            message="Server is healthy",
            timestamp=GetHealthResponse.current_timestamp(),
            status=ServerHealthStatus.HEALTHY,
        )
