class BCBError(Exception):
    """Base exception for all python-bcb errors."""


class BCBAPIError(BCBError):
    """HTTP or API-level error from BCB."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class CurrencyNotFoundError(BCBError):
    """Raised when a requested currency symbol is not found."""


class SGSError(BCBError):
    """Raised for SGS-specific API errors."""


class ODataError(BCBError):
    """Raised for OData query/metadata errors."""
