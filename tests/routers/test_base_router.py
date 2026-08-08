"""Unit tests for the python_template_server.routers.base_router module."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from slowapi import Limiter

from python_template_server.models import BaseResponse
from python_template_server.routers import BaseRouter

MOCK_RATE_LIMIT = "10/minute"


class MockRouter(BaseRouter):
    """Mock implementation of BaseRouter for testing."""

    def mock_method(self, request: Request) -> BaseResponse:
        """Mock API method."""
        return BaseResponse(message="limited endpoint")

    def setup_routes(self) -> None:
        """Set up mock routes for testing."""
        mock_limiter = MagicMock(spec=Limiter)
        mock_limiter.limit = MagicMock(return_value=lambda f: f)

        self.configure(limiter=mock_limiter, rate_limit=MOCK_RATE_LIMIT)
        self.add_route(
            endpoint="/limited",
            handler_function=self.mock_method,
            response_model=BaseResponse,
            methods=["GET"],
            limited=True,
        )
        self.add_route(
            endpoint="/unlimited",
            handler_function=self.mock_method,
            response_model=BaseResponse,
            methods=["GET"],
            limited=False,
        )


@pytest.fixture
def mock_router() -> MockRouter:
    """Fixture to create a mock router instance."""
    router = MockRouter(prefix="/test")
    router.setup_routes()
    return router


class TestBaseRouterInitialization:
    """Unit tests for BaseRouter initialization."""

    def test_base_router_initialization(self, mock_router: MockRouter) -> None:
        """Test that the BaseRouter initializes with the correct prefix and default values."""
        assert mock_router.router.prefix == "/test"


class TestConfigure:
    """Unit tests for the configure method."""

    def test_configure(self, mock_router: BaseRouter) -> None:
        """Test that configure sets the limiter and rate_limit correctly."""
        assert isinstance(mock_router.limiter, Limiter)
        assert mock_router.rate_limit == MOCK_RATE_LIMIT


class TestAddRoutes:
    """Integration tests for the routes in the mock router."""

    def test_add_route(self, mock_router: BaseRouter) -> None:
        """Test add_route with adds routes without authentication."""
        api_routes = [route for route in mock_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        for expected_route in ["/test/limited", "/test/unlimited"]:
            assert expected_route in routes
