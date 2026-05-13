"""
Error handling middleware for the Fraud Detection API.
Sanitizes error responses to prevent information leakage.
"""

import logging
import traceback
from typing import Callable
from uuid import uuid4

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors that are safe to expose to clients."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "API_ERROR"
        super().__init__(message)


class ValidationError(APIError):
    """Validation error - safe to expose details."""

    def __init__(self, message: str):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR")


class AuthenticationError(APIError):
    """Authentication error - safe to expose."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_ERROR")


class AuthorizationError(APIError):
    """Authorization error - safe to expose."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN, "AUTHORIZATION_ERROR")


class NotFoundError(APIError):
    """Resource not found - safe to expose."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status.HTTP_404_NOT_FOUND, "NOT_FOUND")


class RateLimitError(APIError):
    """Rate limit exceeded - safe to expose."""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT_EXCEEDED")


class ServiceUnavailableError(APIError):
    """Service unavailable - safe to expose."""

    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")


# Error messages for internal errors (do NOT expose actual error details)
SANITIZED_ERROR_MESSAGES = {
    500: "An internal error occurred. Please try again later.",
    502: "Bad gateway. Please try again later.",
    503: "Service temporarily unavailable. Please try again later.",
    504: "Request timeout. Please try again later.",
}


def _get_error_id() -> str:
    """Generate a unique error ID for tracking."""
    return str(uuid4())[:8]


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches all exceptions and returns sanitized error responses.

    - Known APIError subclasses: Returns the error message (safe)
    - Unknown exceptions: Returns generic message with error_id for tracking
    """

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response

        except APIError as e:
            # Known API errors - safe to expose
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.error_code,
                    "message": e.message,
                },
            )

        except Exception as e:
            # Unknown errors - sanitize and log
            error_id = _get_error_id()

            # Log the full error with traceback for debugging
            logger.error(
                f"Unhandled error [error_id={error_id}]: {type(e).__name__}: {str(e)}\n"
                f"Request: {request.method} {request.url}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )

            # Return sanitized response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": SANITIZED_ERROR_MESSAGES[500],
                    "error_id": error_id,  # Include for support/debugging
                },
            )


async def api_error_handler(request: Request, exc: APIError):
    """FastAPI exception handler for APIError."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """FastAPI exception handler for unhandled exceptions."""
    error_id = _get_error_id()

    logger.error(
        f"Unhandled error [error_id={error_id}]: {type(exc).__name__}: {str(exc)}\n"
        f"Request: {request.method} {request.url}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": SANITIZED_ERROR_MESSAGES[500],
            "error_id": error_id,
        },
    )
