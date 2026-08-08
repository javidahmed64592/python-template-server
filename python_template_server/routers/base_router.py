"""Base router for the FastAPI server."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from fastapi import APIRouter
from pydantic import BaseModel
from slowapi import Limiter

logger = logging.getLogger(__name__)


class BaseRouter(ABC):
    """Abstract base class for API routers."""

    def __init__(self, prefix: str) -> None:
        """Initialize the base router."""
        logger.info("Initializing router with prefix: %s", prefix or "/")
        self.router = APIRouter(prefix=prefix)

        self.limiter: Limiter | None
        self.rate_limit: str

    @abstractmethod
    def setup_routes(self) -> None:
        """Abstract method to set up API routes."""
        pass

    def configure(self, limiter: Limiter | None, rate_limit: str) -> None:
        """Configure the router with shared dependencies.

        :param Limiter | None limiter: The rate limiter instance to use for this router
        :param str rate_limit: The rate limit string to apply to limited routes
        """
        self.limiter = limiter
        self.rate_limit = rate_limit

    def add_route(
        self,
        endpoint: str,
        handler_function: Callable,
        response_model: type[BaseModel] | None,
        methods: list[str],
        limited: bool,  # noqa: FBT001
    ) -> None:
        """Add an API route.

        :param str endpoint: The API endpoint path
        :param Callable handler_function: The handler function for the endpoint
        :param BaseModel | None response_model: The Pydantic model for the response
        :param list[str] methods: The HTTP methods for the endpoint
        :param bool limited: Whether to apply rate limiting to this route
        """
        try:
            if limited and self.limiter is not None:
                handler_function = self.limiter.limit(self.rate_limit)(handler_function)

            self.router.add_api_route(
                path=endpoint,
                endpoint=handler_function,
                methods=methods,
                response_model=response_model,
            )
        except AttributeError as e:
            error_msg = "Router not configured with limiter and rate limit. Call configure() before adding routes."
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
