"""Unit tests for the python_template_server.template_server module."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
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
    BaseResponse,
    ResponseCode,
    ServerHealthStatus,
    TemplateServerConfig,
)
from python_template_server.template_server import TemplateServer


@pytest.fixture
def mock_verify_token() -> Generator[MagicMock, None, None]:
    """Mock the verify_token function."""
    with patch("python_template_server.template_server.verify_token") as mock_verify:
        yield mock_verify


@pytest.fixture(autouse=True)
def mock_load_hashed_token() -> Generator[MagicMock, None, None]:
    """Mock the load_hashed_token function."""
    with patch("python_template_server.template_server.load_hashed_token") as mock_load:
        mock_load.return_value = "mock_hashed_token"
        yield mock_load


@pytest.fixture
def mock_timestamp() -> Generator[str, None, None]:
    """Mock the current_timestamp method to return a fixed timestamp."""
    fixed_timestamp = "2025-11-22T12:00:00.000000Z"
    with patch("python_template_server.models.BaseResponse.current_timestamp", return_value=fixed_timestamp):
        yield fixed_timestamp


@pytest.fixture
def mock_template_server(mock_app_config: TemplateServerConfig) -> MockTemplateServer:
    """Provide a MockTemplateServer instance for testing."""
    return MockTemplateServer(mock_app_config)


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

    def setup_routes(self) -> None:
        """Set up mock routes for testing."""
        super().setup_routes()
        self.add_unauthenticated_route("/unauthenticated-endpoint", self.mock_unprotected_method, BaseResponse)
        self.add_authenticated_route("/authenticated-endpoint", self.mock_protected_method, BaseResponse)


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


class TestPrometheusMetrics:
    """Unit tests for Prometheus metrics functionality."""

    def test_metrics_endpoint_exists(self, mock_template_server: TemplateServer) -> None:
        """Test that /metrics endpoint is exposed."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        assert "/metrics" in routes

    def test_metrics_setup(self, mock_template_server: TemplateServer) -> None:
        """Test that Prometheus metrics are properly initialized."""
        assert mock_template_server.token_configured_gauge is not None
        assert mock_template_server.auth_success_counter is not None
        assert mock_template_server.auth_failure_counter is not None
        assert mock_template_server.rate_limit_exceeded_counter is not None

    def test_set_token_configured_gauge(self, mock_template_server: TemplateServer) -> None:
        """Test that token_configured_gauge is set correctly."""
        # Initially, the token is configured in the mock_template_server fixture
        assert mock_template_server.token_configured_gauge._value.get() == 1

        # Simulate token not configured
        mock_template_server.hashed_token = ""
        asyncio.run(mock_template_server.get_health(MagicMock()))
        assert mock_template_server.token_configured_gauge._value.get() == 0

    def test_auth_success_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_success_counter is incremented on successful authentication."""
        mock_verify_token.return_value = True
        initial_value = mock_template_server.auth_success_counter._value.get()

        asyncio.run(mock_template_server._verify_api_key(api_key="valid_token"))

        assert mock_template_server.auth_success_counter._value.get() == initial_value + 1

    def test_auth_failure_missing_metric_incremented(self, mock_template_server: TemplateServer) -> None:
        """Test that auth_failure_counter is incremented when API key is missing."""
        initial_value = mock_template_server.auth_failure_counter.labels(reason="missing")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key=None))

        assert mock_template_server.auth_failure_counter.labels(reason="missing")._value.get() == initial_value + 1

    def test_auth_failure_invalid_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_failure_counter is incremented when API key is invalid."""
        mock_verify_token.return_value = False
        initial_value = mock_template_server.auth_failure_counter.labels(reason="invalid")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key="invalid_token"))

        assert mock_template_server.auth_failure_counter.labels(reason="invalid")._value.get() == initial_value + 1

    def test_auth_failure_error_metric_incremented(
        self, mock_template_server: TemplateServer, mock_verify_token: MagicMock
    ) -> None:
        """Test that auth_failure_counter is incremented when verification raises ValueError."""
        mock_verify_token.side_effect = ValueError("Verification error")
        initial_value = mock_template_server.auth_failure_counter.labels(reason="error")._value.get()

        with pytest.raises(HTTPException):
            asyncio.run(mock_template_server._verify_api_key(api_key="error_token"))

        assert mock_template_server.auth_failure_counter.labels(reason="error")._value.get() == initial_value + 1


class TestRateLimiting:
    """Unit tests for rate limiting functionality."""

    def test_rate_limit_exception_handler(self, mock_template_server: TemplateServer) -> None:
        """Test that _rate_limit_exception_handler increments counter and returns expected response."""
        request = MagicMock(spec=Request)

        # Use a mock exception with retry_after attribute to avoid constructor requirement
        exc = MagicMock(spec=RateLimitExceeded)
        exc.retry_after = 42

        initial_value = mock_template_server.rate_limit_exceeded_counter.labels(endpoint=request.url.path)._value.get()

        # Call the handler
        response = asyncio.run(mock_template_server._rate_limit_exception_handler(request, exc))

        # Verify counter incremented
        assert (
            mock_template_server.rate_limit_exceeded_counter.labels(endpoint=request.url.path)._value.get()
            == initial_value + 1
        )

        # Verify JSONResponse status and content
        assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
        assert isinstance(response.body, bytes)
        assert json.loads(response.body.decode()) == {"detail": "Rate limit exceeded"}
        assert response.headers.get("Retry-After") == str(exc.retry_after)

    def test_setup_rate_limiting_enabled(self, mock_app_config: TemplateServerConfig) -> None:
        """Test rate limiting setup when enabled."""
        mock_app_config.rate_limit.enabled = True

        server = MockTemplateServer(mock_app_config)

        assert server.limiter is not None
        assert server.app.state.limiter is not None

    def test_setup_rate_limiting_disabled(self, mock_app_config: TemplateServerConfig) -> None:
        """Test rate limiting setup when disabled."""
        server = MockTemplateServer(mock_app_config)

        assert server.limiter is None

    def test_limit_route_with_limiter_enabled(self, mock_app_config: TemplateServerConfig) -> None:
        """Test _limit_route when rate limiting is enabled."""
        mock_app_config.rate_limit.enabled = True

        server = MockTemplateServer(mock_app_config)

        limited_route = server._limit_route(server.mock_unprotected_method)
        assert limited_route != server.mock_unprotected_method
        assert hasattr(limited_route, "__wrapped__")

    def test_limit_route_with_limiter_disabled(self, mock_app_config: TemplateServerConfig) -> None:
        """Test _limit_route when rate limiting is disabled."""
        server = MockTemplateServer(mock_app_config)

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
        assert "GET" in test_route.methods
        assert test_route.response_model == BaseResponse

    def test_setup_routes(self, mock_template_server: MockTemplateServer) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_template_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = ["/health", "/metrics", "/unauthenticated-endpoint", "/authenticated-endpoint"]
        for endpoint in expected_endpoints:
            assert endpoint in routes


class TestHealthEndpoint:
    """Integration tests for the /health endpoint."""

    def test_get_health(self, mock_template_server: TemplateServer) -> None:
        """Test the /health endpoint method."""
        request = MagicMock()
        response = asyncio.run(mock_template_server.get_health(request))

        assert response.code == ResponseCode.OK
        assert response.message == "Server is healthy"
        assert response.status == ServerHealthStatus.HEALTHY
        assert mock_template_server.token_configured_gauge._value.get() == 1

    def test_get_health_token_not_configured(self, mock_template_server: TemplateServer) -> None:
        """Test the /health endpoint method when token is not configured."""
        mock_template_server.hashed_token = ""
        request = MagicMock()

        response = asyncio.run(mock_template_server.get_health(request))

        assert response.code == ResponseCode.INTERNAL_SERVER_ERROR
        assert response.message == "Server token is not configured"
        assert response.status == ServerHealthStatus.UNHEALTHY
        assert mock_template_server.token_configured_gauge._value.get() == 0

    def test_health_endpoint(
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
