from __future__ import annotations


class BCBError(Exception):
    """Base exception for all python-bcb errors."""


class BCBAPIError(BCBError):
    """HTTP or API-level error from BCB."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class BCBAPINotFoundError(BCBAPIError):
    """Raised when API returns 404 Not Found."""

    pass


class BCBRateLimitError(BCBAPIError):
    """Raised when API returns 429 Too Many Requests (rate limit exceeded)."""

    pass


class BCBAPIServerError(BCBAPIError):
    """Raised when API returns 5xx Server Error."""

    pass


class CurrencyNotFoundError(BCBError):
    """Raised when a requested currency symbol is not found."""


class SGSError(BCBError):
    """Raised for SGS-specific API errors."""


class ODataError(BCBError):
    """Raised for OData query/metadata errors."""
