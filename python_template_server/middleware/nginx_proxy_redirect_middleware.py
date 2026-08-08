"""Middleware to redirect direct access to nginx proxy."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp

from python_template_server.models import ResponseCode


class NginxProxyRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to redirect requests not coming through nginx proxy to the proxied URL."""

    def __init__(self, app: ASGIApp, proxy_url: str) -> None:
        """Initialize the NginxProxyRedirectMiddleware.

        :param ASGIApp app: The ASGI application
        :param str proxy_url: The nginx proxy URL
        """
        super().__init__(app)
        self.logger = logging.getLogger(__name__)
        self.proxy_url = proxy_url

    def _get_redirect_url(self, request: Request) -> str:
        """Construct the redirect URL based on the request path and query parameters.

        :param Request request: The incoming request
        :return: The constructed redirect URL
        :rtype: str
        """
        path = str(request.url.path)
        query = str(request.url.query)
        return f"{self.proxy_url}{path}{f'?{query}' if query else ''}"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Check if request is from nginx proxy or localhost, redirect if not.

        Nginx sets the X-Forwarded-Proto header. If this header is missing,
        the request is coming directly to the app and should be redirected
        to the nginx-proxied URL, where nginx will handle authentication.
        """
        client_host = request.client.host if request.client else "unknown"
        if client_host == "127.0.0.1" or "x-forwarded-proto" in request.headers:
            return await call_next(request)

        redirect_url = self._get_redirect_url(request)

        self.logger.warning(
            "Direct access detected from %s - redirecting to nginx proxy: %s",
            client_host,
            redirect_url,
        )

        return RedirectResponse(url=redirect_url, status_code=ResponseCode.REDIRECT)
