"""
Correlation ID middleware for request tracing.

Adds/propagates an `X-Correlation-ID` header on all requests and responses.
Stores the value in a context variable for logging correlation.

Security & Privacy:
- Correlation IDs are random UUIDs; they contain no PII.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable storing current correlation ID
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Starlette middleware to manage correlation ID lifecycle."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = incoming if incoming else str(uuid.uuid4())
        token = correlation_id_var.set(correlation_id)
        try:
            request.state.correlation_id = correlation_id
            response: Response = await call_next(request)
        except Exception:
            # Ensure correlationId is present in error responses as well
            logger.exception("Unhandled exception during request processing")
            raise
        finally:
            # Ensure the correlation ID is set on the outbound response header
            try:
                # Response may not exist if exception occurred before call_next, handled by exception handlers
                pass
            finally:
                correlation_id_var.reset(token)
        # Add/overwrite the header on successful responses
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
