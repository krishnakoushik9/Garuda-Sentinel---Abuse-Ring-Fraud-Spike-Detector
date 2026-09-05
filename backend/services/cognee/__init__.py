"""Cognee Cloud Integration Layer.

This module acts as the ONLY gateway to the Cognee Cloud API.
"""

from .exceptions import (
    CogneeException,
    CogneeConnectionException,
    CogneeAuthException,
    CogneeRateLimitException,
    CogneeValidationException,
    CogneeServerException,
)
from .models import (
    TenantInfo,
    ApiKeyInfo,
    ApiKeyCreateResponse,
    SubscriptionStatus,
    BillingInfo,
    HealthCheckResult,
    ServiceUrlInfo,
)
from .client import CogneeClient
from .service import CogneeService

__all__ = [
    "CogneeException",
    "CogneeConnectionException",
    "CogneeAuthException",
    "CogneeRateLimitException",
    "CogneeValidationException",
    "CogneeServerException",
    "TenantInfo",
    "ApiKeyInfo",
    "ApiKeyCreateResponse",
    "SubscriptionStatus",
    "BillingInfo",
    "HealthCheckResult",
    "ServiceUrlInfo",
    "CogneeClient",
    "CogneeService",
]
