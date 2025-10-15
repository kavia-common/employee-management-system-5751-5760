"""
Error utilities for [STUB] backend.

Provides helpers for raising HTTP errors with consistent messages.
"""
from __future__ import annotations

from fastapi import HTTPException, status


# PUBLIC_INTERFACE
def http_error(status_code: int, message: str) -> HTTPException:
    """Return an HTTPException with a standardized message. [STUB]"""
    # This can be expanded to include correlation IDs or error codes.
    return HTTPException(status_code=status_code, detail=message)


# Common shortcuts

# PUBLIC_INTERFACE
def bad_request(msg: str) -> HTTPException:
    """Return 400 Bad Request HTTPException. [STUB]"""
    return http_error(status.HTTP_400_BAD_REQUEST, msg)


# PUBLIC_INTERFACE
def unauthorized(msg: str) -> HTTPException:
    """Return 401 Unauthorized HTTPException. [STUB]"""
    return http_error(status.HTTP_401_UNAUTHORIZED, msg)


# PUBLIC_INTERFACE
def forbidden(msg: str) -> HTTPException:
    """Return 403 Forbidden HTTPException. [STUB]"""
    return http_error(status.HTTP_403_FORBIDDEN, msg)


# PUBLIC_INTERFACE
def not_found(msg: str) -> HTTPException:
    """Return 404 Not Found HTTPException. [STUB]"""
    return http_error(status.HTTP_404_NOT_FOUND, msg)


# PUBLIC_INTERFACE
def conflict(msg: str) -> HTTPException:
    """Return 409 Conflict HTTPException. [STUB]"""
    return http_error(status.HTTP_409_CONFLICT, msg)


# PUBLIC_INTERFACE
def unprocessable(msg: str) -> HTTPException:
    """Return 422 Unprocessable Entity HTTPException. [STUB]"""
    return http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, msg)
