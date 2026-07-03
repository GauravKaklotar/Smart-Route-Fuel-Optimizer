"""
Custom DRF exception handler for Spotter AI.

Intercepts all exceptions and returns structured JSON error responses.
Never exposes raw exception details in production.
"""

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Wrap DRF's default exception handler to return consistent error format.

    Response shape:
        {
            "error": {
                "type": "validation_error",
                "message": "Human-readable message",
                "details": { ... }   # optional, validation errors only
            }
        }
    """
    # Let DRF handle its own exceptions first
    response = exception_handler(exc, context)

    if response is not None:
        error_type = _classify_error(response.status_code)
        error_body: dict[str, Any] = {
            "type": error_type,
            "message": _extract_message(response.data),
        }

        # Preserve field-level validation details
        if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(
            response.data, dict
        ):
            error_body["details"] = response.data

        response.data = {"error": error_body}
        return response

    # Unhandled exception — log it, return generic 500
    logger.exception("Unhandled exception in %s", context.get("view", "unknown"))
    return Response(
        {
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _classify_error(status_code: int) -> str:
    """Map HTTP status code to a human-readable error type."""
    mapping = {
        400: "validation_error",
        401: "authentication_error",
        403: "permission_denied",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "upstream_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "error")


def _extract_message(data: Any) -> str:
    """Extract a single human-readable message from DRF error data."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return str(data[0]) if data else "An error occurred."
    if isinstance(data, dict):
        # Try common keys first
        for key in ("detail", "message", "non_field_errors"):
            if key in data:
                value = data[key]
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
        # Fall back to first field error
        for _field, errors in data.items():
            if isinstance(errors, list) and errors:
                return str(errors[0])
            return str(errors)
    return "An error occurred."
