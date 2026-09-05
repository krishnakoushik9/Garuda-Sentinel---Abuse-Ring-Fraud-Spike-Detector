"""Cognee Integration Exceptions."""

class CogneeException(Exception):
    """Base exception for all Cognee integration errors."""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class CogneeConnectionException(CogneeException):
    """Raised when the client cannot connect to the Cognee Cloud service (DNS or transport errors)."""
    pass


class CogneeAuthException(CogneeException):
    """Raised when authentication (API Key or Tenant ID verification) fails."""
    pass


class CogneeRateLimitException(CogneeException):
    """Raised when the client is rate limited by the Cognee Cloud API (429 status code)."""
    pass


class CogneeValidationException(CogneeException):
    """Raised when input validation fails locally or on the server side."""
    pass


class CogneeServerException(CogneeException):
    """Raised when the Cognee Cloud server returns an internal error (5xx status code)."""
    pass
