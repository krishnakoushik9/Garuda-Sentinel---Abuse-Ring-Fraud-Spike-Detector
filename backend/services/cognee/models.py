"""Cognee Integration Response Models."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TenantInfo(BaseModel):
    """Details of the current active Cognee tenant."""
    tenant_id: str = Field(..., description="The unique UUID of the tenant")
    user_id: str = Field(..., description="The UUID of the owner user")
    name: str = Field(..., description="Name of the workspace or organization")
    is_active: bool = Field(True, description="Whether the tenant is currently active")


class ApiKeyInfo(BaseModel):
    """Information about an active Cognee Cloud API Key."""
    key_id: str = Field(..., description="Unique ID identifier for the API key")
    name: str = Field(..., description="A friendly name for the key")
    prefix: str = Field(..., description="Masked preview of the key, e.g. cog_***")
    created_at: str = Field(..., description="ISO timestamp representing key creation time")
    last_used: Optional[str] = Field(None, description="ISO timestamp of last key usage")


class ApiKeyCreateResponse(BaseModel):
    """Response returned when generating a new API Key."""
    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="A friendly name for the key")
    api_key: str = Field(..., description="The full plaintext API key. Only shown once.")
    created_at: str = Field(..., description="ISO timestamp representing key creation time")


class SubscriptionStatus(BaseModel):
    """Details on the active tenant's plan and usage quotas."""
    plan_name: str = Field(..., description="Name of the subscription tier, e.g. Enterprise Gold")
    status: str = Field(..., description="Status of the subscription, e.g. active, unpaid, trialing")
    expires_at: Optional[str] = Field(None, description="ISO date representing plan renewal or expiration")
    quota_limit: int = Field(..., description="Maximum API calls allowed per billing cycle")
    quota_used: int = Field(..., description="API calls used during the current cycle")


class BillingInfo(BaseModel):
    """Billing summary and credits tracking for the tenant."""
    credits_remaining: float = Field(..., description="Credits balance remaining in USD")
    balance: float = Field(..., description="Total outstanding balance in USD")
    currency: str = Field("USD", description="Currency symbol")
    payment_method: Optional[str] = Field(None, description="Masked payment method, e.g. Visa ****1234")
    subscription_price: float = Field(..., description="Monthly subscription price in USD")


class ServiceUrlInfo(BaseModel):
    """Information about the connected Cognee Cloud service URL."""
    service_url: str = Field(..., description="The full base URL of the targeted Cognee Cloud instance")


class HealthCheckResult(BaseModel):
    """Comprehensive diagnostic health report for the Cognee Cloud service."""
    status: str = Field(..., description="Overall health state ('healthy' or 'unhealthy')")
    authentication: bool = Field(..., description="Whether API key authentication succeeded")
    tenant_verified: bool = Field(..., description="Whether the specified Tenant ID matches the active workspace")
    connectivity: bool = Field(..., description="Whether a network connection to the host could be established")
    latency_ms: float = Field(..., description="Round-trip response latency in milliseconds")
    api_version: str = Field(..., description="API version of the target server")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic key-value pairs")
