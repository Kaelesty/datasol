"""Domain-level exceptions for the Datssol client."""

from __future__ import annotations


class DatssolError(Exception):
    """Base exception for the project."""


class ApiRequestError(DatssolError):
    """Raised when the HTTP request to the game server fails."""


class ApiResponseError(DatssolError):
    """Raised when the server returns an unexpected payload."""

