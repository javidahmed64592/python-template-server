"""Unit tests for the nginx_proxy_redirect_middleware module."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Request, Response

from python_template_server.middleware import NginxProxyRedirectMiddleware
from python_template_server.models import NginxProxyRedirectConfigModel, ResponseCode


class TestNginxProxyRedirectMiddleware:
    """Unit tests for NginxProxyRedirectMiddleware."""

    def test_init(self, mock_app: FastAPI) -> None:
        """Test middleware initialization."""
        config = NginxProxyRedirectConfigModel(app_name="testapp", domain=".example.com")
        middleware = NginxProxyRedirectMiddleware(mock_app, config)
        assert middleware.logger is not None
        assert middleware.config == config

    @pytest.mark.asyncio
    async def test_dispatch_redirects_direct_access(
        self, mock_app: FastAPI, mock_request: Request, mock_nginx_config: NginxProxyRedirectConfigModel
    ) -> None:
        """Test that dispatch redirects direct access to the nginx proxy URL."""
        mock_nginx_config.enabled = True
        middleware = NginxProxyRedirectMiddleware(mock_app, mock_nginx_config)

        # Create a request without the X-Forwarded-Proto header and not from localhost
        mock_request.client = MagicMock(host="192.168.1.1")  # ty: ignore[invalid-assignment]
        mock_request.headers = {}  # ty: ignore[invalid-assignment]

        # Mock the call_next function
        call_next = AsyncMock()

        # Mock the logger
        middleware.logger = MagicMock()

        result = await middleware.dispatch(mock_request, call_next)

        expected_redirect_url = f"https://{mock_nginx_config.app_name}{mock_nginx_config.domain}{mock_request.url.path}?{f'{mock_request.url.query}'}"
        assert isinstance(result, Response)
        assert result.status_code == ResponseCode.REDIRECT
        assert result.headers["location"] == expected_redirect_url

    @pytest.mark.asyncio
    async def test_dispatch_allows_nginx_access(
        self, mock_app: FastAPI, mock_request: Request, mock_nginx_config: NginxProxyRedirectConfigModel
    ) -> None:
        """Test that dispatch allows access when coming from nginx proxy."""
        mock_nginx_config.enabled = True
        middleware = NginxProxyRedirectMiddleware(mock_app, mock_nginx_config)

        # Create a request with the X-Forwarded-Proto header
        mock_request.headers = {"x-forwarded-proto": "https"}  # ty: ignore[invalid-assignment]

        # Mock the call_next function
        mock_response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_allows_localhost_access(
        self, mock_app: FastAPI, mock_request: Request, mock_nginx_config: NginxProxyRedirectConfigModel
    ) -> None:
        """Test that dispatch allows access when coming from localhost."""
        mock_nginx_config.enabled = True
        middleware = NginxProxyRedirectMiddleware(mock_app, mock_nginx_config)

        # Mock the call_next function
        mock_response = MagicMock(spec=Response)
        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        assert result == mock_response
