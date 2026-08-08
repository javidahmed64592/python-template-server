"""Unit tests for the python_template_server.routers.template_server_router module."""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.routing import APIRoute

from python_template_server.models import TemplateServerConfig
from python_template_server.routers import TemplateServerRouter


class TestRoutes:
    """Unit tests for route setup in TemplateServerRouter."""

    def test_setup_routes(self, mock_template_server_router: TemplateServerRouter) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_template_server_router.router.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/auth_enabled",
            "/config",
            "/health",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes


class TestGetHealthEndpoint:
    """Integration tests for the /health endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_health(self, mock_template_server_router: TemplateServerRouter, mock_request_object: Request) -> None:
        """Test the /health endpoint method."""
        response = asyncio.run(mock_template_server_router.get_health(mock_request_object))
        assert response.message == "Server is healthy"
        assert isinstance(response.timestamp, str)


class TestGetConfigEndpoint:
    """Integration tests for the /config endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_config(self, mock_template_server_router: TemplateServerRouter, mock_request_object: Request) -> None:
        """Test the /config endpoint method."""
        response = asyncio.run(mock_template_server_router.get_config(mock_request_object))
        assert isinstance(response.config, TemplateServerConfig)
        assert response.version == mock_template_server_router.version
        assert isinstance(response.timestamp, str)


class TestGetAuthEnabledEndpoint:
    """Integration tests for the /auth_enabled endpoint."""

    @pytest.fixture
    def mock_request_object(self) -> Request:
        """Provide a mock Request object."""
        return MagicMock(spec=Request)

    def test_get_auth_enabled(
        self, mock_template_server_router: TemplateServerRouter, mock_request_object: Request
    ) -> None:
        """Test the /auth_enabled endpoint method."""
        response = asyncio.run(mock_template_server_router.get_auth_enabled(mock_request_object))
        assert isinstance(response.auth_enabled, bool)
        assert isinstance(response.timestamp, str)
