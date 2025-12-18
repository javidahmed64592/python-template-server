"""Unit tests for the python_template_server.template_server module."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from importlib.metadata import PackageMetadata
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.security import APIKeyHeader
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from python_template_server.constants import API_PREFIX
from python_template_server.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from python_template_server.models import (
    BaseMetricNames,
    BaseResponse,
    CustomJSONResponse,
    ResponseCode,
    ServerHealthStatus,
    TemplateServerConfig,
)
from python_template_server.prometheus_handler import PrometheusHandler
from python_template_server.template_server import TemplateServer


@pytest.fixture(autouse=True)
def mock_package_metadata() -> Generator[MagicMock]:
    """Mock importlib.metadata.metadata to return a mock PackageMetadata."""
    with patch("python_template_server.template_server.metadata") as mock_metadata:
        mock_pkg_metadata = MagicMock(spec=PackageMetadata)
        metadata_dict = {
            "Name": "python-template-server",
            "Version": "0.1.0",
            "Summary": "A template FastAPI server with authentication, rate limiting and Prometheus metrics.",
        }
        mock_pkg_metadata.__getitem__.side_effect = lambda key: metadata_dict[key]
        mock_metadata.return_value = mock_pkg_metadata
        yield mock_metadata


@pytest.fixture
def mock_verify_token() -> Generator[MagicMock]:
    """Mock the verify_token function."""
    with patch("python_template_server.template_server.verify_token") as mock_verify:
        yield mock_verify


@pytest.fixture(autouse=True)
def mock_load_hashed_token() -> Generator[MagicMock]:
    """Mock the load_hashed_token function."""
    with patch("python_template_server.template_server.load_hashed_token") as mock_load:
        mock_load.return_value = "mock_hashed_token"
        yield mock_load


@pytest.fixture
def mock_timestamp() -> Generator[str]:
    """Mock the current_timestamp method to return a fixed timestamp."""
    fixed_timestamp = "2025-11-22T12:00:00.000000Z"
    with patch("python_template_server.models.BaseResponse.current_timestamp", return_value=fixed_timestamp):
        yield fixed_timestamp


@pytest.fixture
def mock_template_server(mock_template_server_config: TemplateServerConfig) -> MockTemplateServer:
    """Provide a MockTemplateServer instance for testing."""
    return MockTemplateServer(config=mock_template_server_config)


class MockTemplateServer(TemplateServer):
    """Mock subclass of TemplateServer for testing."""

    def mock_unprotected_method(self, request: Request) -> BaseResponse:
        """Mock unprotected method."""
        return BaseResponse(
            code=ResponseCode.OK, message="unprotected endpoint", timestamp=BaseResponse.current_timestamp()
        )

    def mock_protected_method(self, request: Request) -> BaseResponse:
        """Mock protected method."""
        return BaseResponse(
            code=ResponseCode.OK, message="protected endpoint", timestamp=BaseResponse.current_timestamp()
        )

    def mock_unlimited_unprotected_method(self, request: Request) -> BaseResponse:
        """Mock unlimited unprotected method."""
        return BaseResponse(
            code=ResponseCode.OK, message="unlimited unprotected endpoint", timestamp=BaseResponse.current_timestamp()
        )

    def mock_unlimited_protected_method(self, request: Request) -> BaseResponse:
        """Mock unlimited protected method."""
        return BaseResponse(
            code=ResponseCode.OK, message="unlimited protected endpoint", timestamp=BaseResponse.current_timestamp()
        )

    def validate_config(self, config_data: dict[str, Any]) -> TemplateServerConfig:
        """Validate configuration from the config.json file.

        :param dict config_data: Configuration data
        :return TemplateServerConfig: Loaded configuration
        """
        return super().validate_config(config_data)

    def setup_routes(self) -> None:
        """Set up mock routes for testing."""
        super().setup_routes()
        self.add_unauthenticated_route("/unauthenticated-endpoint", self.mock_unprotected_method, BaseResponse, ["GET"])
        self.add_authenticated_route("/authenticated-endpoint", self.mock_protected_method, BaseResponse, ["POST"])
        self.add_unauthenticated_route(
            "/unlimited-unauthenticated-endpoint",
            self.mock_unlimited_unprotected_method,
            BaseResponse,
            ["GET"],
            limited=False,
        )
        self.add_authenticated_route(
            "/unlimited-authenticated-endpoint",
            self.mock_unlimited_protected_method,
            BaseResponse,
            ["POST"],
            limited=False,
        )


class TestTemplateServer:
    """Unit tests for the TemplateServer class."""

    def test_init(self, mock_template_server: TemplateServer) -> None:
        """Test TemplateServer initialization."""
        assert isinstance(mock_template_server.app, FastAPI)
        assert mock_template_server.app.title == "python-template-server"
        assert (
            mock_template_server.app.description
            == "A template FastAPI server with authentication, rate limiting and Prometheus metrics."
        )
        assert mock_template_server.app.version == "0.1.0"
        assert mock_template_server.app.root_path == API_PREFIX
        assert isinstance(mock_template_server.api_key_header, APIKeyHeader)

    def test_request_middleware_added(self, mock_template_server: TemplateServer) -> None:
        """Test that all middleware is added to the app."""
        middlewares = [middleware.cls for middleware in mock_template_server.app.user_middleware]
        assert RequestLoggingMiddleware in middlewares
        assert SecurityHeadersMiddleware in middlewares

    def test_json_response_configured(
        self, mock_template_server: TemplateServer, mock_template_server_config: TemplateServerConfig
    ) -> None:
        """Test that CustomJSONResponse is properly configured during initialization."""
        # Verify CustomJSONResponse class variables are set correctly
        assert CustomJSONResponse._ensure_ascii == mock_template_server_config.json_response.ensure_ascii
        assert CustomJSONResponse._allow_nan == mock_template_server_config.json_response.allow_nan
        assert CustomJSONResponse._indent == mock_template_server_config.json_response.indent
        assert CustomJSONResponse.media_type == mock_template_server_config.json_response.media_type

        # Test that CustomJSONResponse renders correctly with configured settings
        response = CustomJSONResponse(content={"test": "data", "emoji": "👋"})
        rendered = response.render({"test": "data", "emoji": "👋"})

        # With ensure_ascii=False, emojis should be preserved
        assert "👋".encode() in rendered
        assert b'"test":"data"' in rendered  # Compact format (no spaces)


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_with_filepath_success(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test that load_config is called with the specified filepath when config is None."""
        with patch.object(
            MockTemplateServer, "load_config", return_value=mock_template_server_config
        ) as mock_load_config:
            custom_filepath = Path("/custom/config.json")
            server = MockTemplateServer(config_filepath=custom_filepath)

            mock_load_config.assert_called_once_with(custom_filepath)
            assert server.config == mock_template_server_config

    def test_load_config_with_no_filepath_success(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
        mock_template_server_config: TemplateServerConfig,
    ) -> None:
        """Test successful loading of config."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = json.dumps(mock_template_server_config.model_dump())

        config = MockTemplateServer().config

        assert isinstance(config, TemplateServerConfig)
        assert config == mock_template_server_config
        mock_sys_exit.assert_not_called()

    def test_load_config_file_not_found(
        self,
        mock_exists: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config when the file does not exist."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            MockTemplateServer()

        mock_sys_exit.assert_called_once_with(1)

    def test_load_config_invalid_json(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config with invalid JSON content."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = "invalid json"

        with pytest.raises(SystemExit):
            MockTemplateServer()

        mock_sys_exit.assert_called_with(1)

    def test_load_config_os_error(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config that raises an OSError."""
        mock_exists.return_value = True
        mock_open_file.side_effect = OSError("File read error")

        with pytest.raises(SystemExit):
            MockTemplateServer()

        mock_sys_exit.assert_called_with(1)

    def test_load_config_validation_error(
        self,
        mock_exists: MagicMock,
        mock_open_file: MagicMock,
        mock_sys_exit: MagicMock,
    ) -> None:
        """Test loading config that fails validation."""
        mock_exists.return_value = True
        mock_open_file.return_value.read.return_value = json.dumps({"server": {"host": "localhost", "port": 999999}})

        with pytest.raises(SystemExit):
            MockTemplateServer()

        mock_sys_exit.assert_called_once_with(1)


class TestVerifyApiKey:
    """Unit tests for the _verify_api_key method."""

    def test_verify_api_key_valid(self, mock_template_server: TemplateServer, mock_verify_token: MagicMock) -> None:
        """Test _verify_api_key with valid API key."""
        mock_verify_token.return_value = True

        result = asyncio.run(mock_template_server._verify_api_key("valid_key"))
        assert result is None

    def test_verify_api_key_missing(self, mock_template_server: TemplateServer) -> None:
        """Test _verify_api_key with missing API key."""
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_template_server._verify_api_key(None))

        assert exc_info.value.status_code == ResponseCode.UNAUTHORIZED
        assert exc_info.value.detail == "Missing API key"

    def test_verify_api_key_invalid(self, mock_template_server: TemplateServer, mock_verify_token: MagicMock) -> None:
        """Test _verify_api_key with invalid API key."""
        mock_verify_token.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_template_server._verify_api_key("invalid_key"))

        assert exc_info.value.status_code == ResponseCode.UNAUTHORIZED
        assert exc_info.value.detail == "Invalid API key"

    def test_verify_api_key_value_error(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test _verify_api_key when verify_token raises ValueError."""
        mock_verify_token.side_effect = ValueError("No stored token hash found")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(mock_template_server._verify_api_key("some_key"))

        assert exc_info.value.status_code == ResponseCode.UNAUTHORIZED
        assert "No stored token hash found" in exc_info.value.detail

    def test_auth_success_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_success_counter is incremented on successful authentication."""
        mock_verify_token.return_value = True
        auth_success_counter = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.AUTH_SUCCESS_TOTAL)
        assert auth_success_counter is not None
        initial_value = auth_success_counter._value.get()

        asyncio.run(mock_template_server._verify_api_key(api_key="valid_token"))

        assert auth_success_counter._value.get() == initial_value + 1

    def test_auth_failure_missing_metric_incremented(self, mock_template_server: TemplateServer) -> None:
        """Test that auth_failure_counter is incremented when API key is missing."""
        auth_failure_counter = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.AUTH_FAILURE_TOTAL)
        assert auth_failure_counter is not None
        initial_value = auth_failure_counter.labels(reason="missing")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key=None))

        assert auth_failure_counter.labels(reason="missing")._value.get() == initial_value + 1

    def test_auth_failure_invalid_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_failure_counter is incremented when API key is invalid."""
        mock_verify_token.return_value = False
        auth_failure_counter = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.AUTH_FAILURE_TOTAL)
        assert auth_failure_counter is not None
        initial_value = auth_failure_counter.labels(reason="invalid")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key="invalid_token"))

        assert auth_failure_counter.labels(reason="invalid")._value.get() == initial_value + 1

    def test_auth_failure_error_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_failure_counter is incremented when verification raises ValueError."""
        mock_verify_token.side_effect = ValueError("Verification error")
        auth_failure_counter = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.AUTH_FAILURE_TOTAL)
        assert auth_failure_counter is not None
        initial_value = auth_failure_counter.labels(reason="error")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key="error_token"))

        assert auth_failure_counter.labels(reason="error")._value.get() == initial_value + 1


class TestPrometheusMetrics:
    """Unit tests for Prometheus metrics functionality."""

    def test_metrics_setup(self, mock_template_server: TemplateServer) -> None:
        """Test that Prometheus metrics are properly initialized."""
        assert isinstance(mock_template_server.prometheus_handler, PrometheusHandler)
        assert mock_template_server.prometheus_handler.get_metric(BaseMetricNames.TOKEN_CONFIGURED)._value.get() == 1

    def test_metrics_endpoint_exists(self, mock_template_server: TemplateServer) -> None:
        """Test that /metrics endpoint is exposed."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/metrics" in routes


class TestRateLimiting:
    """Unit tests for rate limiting functionality."""

    def test_rate_limit_exception_handler(self, mock_template_server: TemplateServer) -> None:
        """Test that _rate_limit_exception_handler increments counter and returns expected response."""
        request = MagicMock(spec=Request)

        # Use a mock exception with retry_after attribute to avoid constructor requirement
        exc = MagicMock(spec=RateLimitExceeded)
        exc.retry_after = 42

        rate_limit_counter = mock_template_server.prometheus_handler.get_metric(
            BaseMetricNames.RATE_LIMIT_EXCEEDED_TOTAL
        )
        assert rate_limit_counter is not None
        initial_value = rate_limit_counter.labels(endpoint=request.url.path)._value.get()

        # Call the handler
        response = asyncio.run(mock_template_server._rate_limit_exception_handler(request, exc))

        # Verify counter incremented
        assert rate_limit_counter.labels(endpoint=request.url.path)._value.get() == initial_value + 1

        # Verify JSONResponse status and content
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert isinstance(response.body, bytes)
        assert json.loads(response.body.decode()) == {"detail": "Rate limit exceeded"}
        assert response.headers.get("Retry-After") == str(exc.retry_after)

    def test_setup_rate_limiting_enabled(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test rate limiting setup when enabled."""
        mock_template_server_config.rate_limit.enabled = True

        server = MockTemplateServer(config=mock_template_server_config)

        assert server.limiter is not None
        assert server.app.state.limiter is not None

    def test_setup_rate_limiting_disabled(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test rate limiting setup when disabled."""
        server = MockTemplateServer(config=mock_template_server_config)

        assert server.limiter is None

    def test_limit_route_with_limiter_enabled(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test _limit_route when rate limiting is enabled."""
        mock_template_server_config.rate_limit.enabled = True

        server = MockTemplateServer(config=mock_template_server_config)

        limited_route = server._limit_route(server.mock_unprotected_method)
        assert limited_route != server.mock_unprotected_method
        assert hasattr(limited_route, "__wrapped__")

    def test_limit_route_with_limiter_disabled(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test _limit_route when rate limiting is disabled."""
        server = MockTemplateServer(config=mock_template_server_config)

        limited_route = server._limit_route(server.mock_unprotected_method)
        assert limited_route == server.mock_unprotected_method


class TestTemplateServerRun:
    """Unit tests for TemplateServer.run method."""

    def test_run_success(self, mock_template_server: TemplateServer, mock_exists: MagicMock) -> None:
        """Test successful server run."""
        mock_exists.side_effect = [True, True]

        with patch("python_template_server.template_server.uvicorn.run") as mock_uvicorn_run:
            mock_template_server.run()

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args.kwargs
        assert call_kwargs["host"] == mock_template_server.config.server.host
        assert call_kwargs["port"] == mock_template_server.config.server.port

    def test_run_missing_cert_file(self, mock_template_server: TemplateServer, mock_exists: MagicMock) -> None:
        """Test run raises SystemExit when certificate file is missing."""
        mock_exists.side_effect = [False, True]

        with pytest.raises(SystemExit):
            mock_template_server.run()

    def test_run_missing_key_file(self, mock_template_server: TemplateServer, mock_exists: MagicMock) -> None:
        """Test run raises SystemExit when key file is missing."""
        mock_exists.side_effect = [True, False]

        with pytest.raises(SystemExit):
            mock_template_server.run()

    def test_run_os_error(self, mock_template_server: TemplateServer, mock_exists: MagicMock) -> None:
        """Test run raises SystemExit on OSError."""
        mock_exists.side_effect = [True, True]

        with patch("python_template_server.template_server.uvicorn.run") as mock_uvicorn_run:
            mock_uvicorn_run.side_effect = OSError("Test OSError")

            with pytest.raises(SystemExit):
                mock_template_server.run()


class TestTemplateServerRoutes:
    """Integration tests for the mock routes in MockTemplateServer."""

    def test_add_unauthenticated_route(self, mock_template_server: MockTemplateServer) -> None:
        """Test add_unauthenticated_route adds routes without authentication."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/unauthenticated-endpoint" in routes

        # Find the specific route and verify it has no dependencies (unauthenticated)
        test_route = next((route for route in api_routes if route.path == "/unauthenticated-endpoint"), None)
        assert test_route is not None

        # Verify the route has no dependencies (unauthenticated)
        assert len(test_route.dependencies) == 0

        # Verify method and response model
        assert "GET" in test_route.methods
        assert test_route.response_model == BaseResponse

    def test_add_authenticated_route(self, mock_template_server: MockTemplateServer) -> None:
        """Test add_authenticated_route adds routes with authentication."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/authenticated-endpoint" in routes

        # Find the specific route
        test_route = next((route for route in api_routes if route.path == "/authenticated-endpoint"), None)
        assert test_route is not None

        # Verify the route has dependencies (authentication)
        assert len(test_route.dependencies) > 0
        dependency = test_route.dependencies[0]
        assert dependency.dependency == mock_template_server._verify_api_key

        # Verify method and response model
        assert "POST" in test_route.methods
        assert test_route.response_model == BaseResponse

    def test_limited_parameter_with_rate_limiting_enabled(
        self, mock_template_server_config: TemplateServerConfig
    ) -> None:
        """Test that limited=True applies rate limiting when limiter is enabled."""
        mock_template_server_config.rate_limit.enabled = True
        server = MockTemplateServer(config=mock_template_server_config)

        # Get the limited routes
        api_routes = [route for route in server.app.routes if isinstance(route, APIRoute)]
        limited_route = next((route for route in api_routes if route.path == "/unauthenticated-endpoint"), None)
        unlimited_route = next(
            (route for route in api_routes if route.path == "/unlimited-unauthenticated-endpoint"), None
        )

        assert limited_route is not None
        assert unlimited_route is not None

        # Limited route should have the limiter wrapper
        assert hasattr(limited_route.endpoint, "__wrapped__")
        # Unlimited route should not have the limiter wrapper
        assert not hasattr(unlimited_route.endpoint, "__wrapped__")

    def test_authenticated_route_limited_parameter(self, mock_template_server_config: TemplateServerConfig) -> None:
        """Test that limited parameter works correctly for authenticated routes."""
        mock_template_server_config.rate_limit.enabled = True
        server = MockTemplateServer(config=mock_template_server_config)

        # Get the authenticated routes
        api_routes = [route for route in server.app.routes if isinstance(route, APIRoute)]
        limited_route = next((route for route in api_routes if route.path == "/authenticated-endpoint"), None)
        unlimited_route = next(
            (route for route in api_routes if route.path == "/unlimited-authenticated-endpoint"), None
        )

        assert limited_route is not None
        assert unlimited_route is not None

        # Both routes should have authentication dependencies
        assert len(limited_route.dependencies) > 0
        assert len(unlimited_route.dependencies) > 0

        # Limited route should have the limiter wrapper
        assert hasattr(limited_route.endpoint, "__wrapped__")
        # Unlimited route should not have the limiter wrapper
        assert not hasattr(unlimited_route.endpoint, "__wrapped__")

    def test_setup_routes(self, mock_template_server: MockTemplateServer) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/health",
            "/login",
            "/metrics",
            "/unauthenticated-endpoint",
            "/authenticated-endpoint",
            "/unlimited-unauthenticated-endpoint",
            "/unlimited-authenticated-endpoint",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes


class TestGetHealthEndpoint:
    """Integration tests for the /health endpoint."""

    def test_get_health(self, mock_template_server: TemplateServer) -> None:
        """Test the /health endpoint method."""
        request = MagicMock()
        response = asyncio.run(mock_template_server.get_health(request))

        assert response.code == ResponseCode.OK
        assert response.message == "Server is healthy"
        assert response.status == ServerHealthStatus.HEALTHY
        token_gauge = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.TOKEN_CONFIGURED)
        assert token_gauge is not None
        assert token_gauge._value.get() == 1

    def test_get_health_token_not_configured(self, mock_template_server: TemplateServer) -> None:
        """Test the /health endpoint method when token is not configured."""
        mock_template_server.hashed_token = ""
        request = MagicMock()

        response = asyncio.run(mock_template_server.get_health(request))

        assert response.code == ResponseCode.INTERNAL_SERVER_ERROR
        assert response.message == "Server token is not configured"
        assert response.status == ServerHealthStatus.UNHEALTHY
        token_gauge = mock_template_server.prometheus_handler.get_metric(BaseMetricNames.TOKEN_CONFIGURED)
        assert token_gauge is not None
        assert token_gauge._value.get() == 0

    def test_get_health_endpoint(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock, mock_timestamp: str
    ) -> None:
        """Test /health endpoint returns 200."""
        mock_verify_token.return_value = True
        app = mock_template_server.app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == ResponseCode.OK
        assert response.json() == {
            "code": ResponseCode.OK,
            "message": "Server is healthy",
            "timestamp": mock_timestamp,
            "status": ServerHealthStatus.HEALTHY,
        }


class TestPostLoginEndpoint:
    """Integration tests for the /login endpoint."""

    def test_post_login(self, mock_template_server: TemplateServer) -> None:
        """Test the /login endpoint method."""
        request = MagicMock()
        response = asyncio.run(mock_template_server.post_login(request))

        assert response.code == ResponseCode.OK
        assert response.message == "Login successful."

    def test_post_login_endpoint(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock, mock_timestamp: str
    ) -> None:
        """Test /login endpoint returns 200."""
        mock_verify_token.return_value = True
        app = mock_template_server.app
        client = TestClient(app)

        response = client.post("/login", headers={"X-API-Key": "test-token"})
        assert response.status_code == ResponseCode.OK
        assert response.json() == {
            "code": ResponseCode.OK,
            "message": "Login successful.",
            "timestamp": mock_timestamp,
        }
