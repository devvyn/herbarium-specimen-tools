"""
Middleware for FastAPI Application

Provides request tracking, logging, and monitoring functionality.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import get_logger

logger = get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Track requests with unique IDs and log request/response details.

    Adds:
    - X-Request-ID header to all responses
    - Request duration logging
    - Request/response logging with structured data
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracking."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Attach request_id to request state for use in handlers
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with request context
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log completed request
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Skip logging for health check endpoints.

    Reduces log noise from frequent health checks.
    """

    HEALTH_PATHS = {"/api/v1/health", "/health", "/healthz", "/ping"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request, skipping logs for health checks."""
        # Bypass logging for health checks
        if request.url.path in self.HEALTH_PATHS:
            response = await call_next(request)
            return response

        # Normal processing for other requests
        response = await call_next(request)
        return response
