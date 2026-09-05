"""Cognee service gateway logic."""

import logging
import time
from typing import List, Optional

from .client import CogneeClient
from .exceptions import CogneeException
from .models import (
    TenantInfo,
    ApiKeyInfo,
    ApiKeyCreateResponse,
    SubscriptionStatus,
    BillingInfo,
    ServiceUrlInfo,
    HealthCheckResult,
)
from .utils import LatencyTimer

logger = logging.getLogger("cognee.service")

class CogneeService:
    """The central gateway service class for Cognee Cloud operations.
    
    Acts as the single point of entry to communicate with the Cognee Cloud.
    """
    
    def __init__(self, client: Optional[CogneeClient] = None):
        self.client = client or CogneeClient()

    async def verify_connection(self) -> bool:
        """Verifies if the client can establish connectivity and authenticate."""
        try:
            # We call the health endpoint to check credentials and endpoint reachability
            await self.client.request("GET", "health")
            logger.info("Cognee Cloud connection verification: SUCCESS")
            return True
        except CogneeException as ce:
            logger.warning(f"Cognee Cloud connection verification: FAILED ({ce.message})")
            return False
        except Exception as e:
            logger.error(f"Cognee Cloud connection verification: ERROR ({e})")
            return False

    async def get_current_tenant(self) -> TenantInfo:
        """Retrieves details of the active workspace tenant."""
        response = await self.client.request("GET", "api/v1/permissions/tenants/current")
        return TenantInfo(**response)

    async def get_service_url(self) -> ServiceUrlInfo:
        """Returns the configured service URL information."""
        return ServiceUrlInfo(service_url=self.client.base_url)

    async def get_subscription_status(self) -> SubscriptionStatus:
        """Retrieves active subscription plan details and quotas."""
        response = await self.client.request("GET", "api/v1/subscriptions/status")
        return SubscriptionStatus(**response)

    async def get_billing(self) -> BillingInfo:
        """Retrieves the credit balance and billing information."""
        response = await self.client.request("GET", "api/v1/billing")
        return BillingInfo(**response)

    async def list_api_keys(self) -> List[ApiKeyInfo]:
        """Lists active API Keys generated for the current tenant."""
        response = await self.client.request("GET", "api/v1/api-keys")
        return [ApiKeyInfo(**item) for item in response]

    async def create_api_key(self, name: str) -> ApiKeyCreateResponse:
        """Generates a new API Key for authentication."""
        data = {"name": name}
        response = await self.client.request("POST", "api/v1/api-keys", data=data)
        return ApiKeyCreateResponse(**response)

    async def delete_api_key(self, key_id: str) -> bool:
        """Deletes an existing API Key."""
        await self.client.request("DELETE", f"api/v1/api-keys/{key_id}")
        logger.info(f"Deleted API Key: {key_id}")
        return True

    async def health_check(self) -> HealthCheckResult:
        """Executes a diagnostic health check of the Cognee Cloud service."""
        connectivity = False
        authentication = False
        tenant_verified = False
        api_version = "unknown"
        details = {}
        
        with LatencyTimer() as timer:
            try:
                # 1. Check health route (connectivity)
                health_data = await self.client.request("GET", "health")
                connectivity = True
                api_version = health_data.get("version", "1.0.0")
                
                # 2. Check current tenant (authentication and tenant matching)
                tenant_data = await self.client.request("GET", "api/v1/permissions/tenants/current")
                authentication = True
                
                tenant_uuid = tenant_data.get("tenant_id")
                if tenant_uuid == self.client.tenant_id:
                    tenant_verified = True
                
                details = {
                    "tenant_name": tenant_data.get("name", "Unknown"),
                    "user_id": tenant_data.get("user_id", "Unknown"),
                    "mock_mode": self.client.mock_mode,
                }
            except Exception as e:
                details = {
                    "error": str(e),
                    "mock_mode": self.client.mock_mode
                }
                logger.warning(f"Cognee health check diagnostics failed: {e}")
                
        latency = timer.elapsed_ms
        status = "healthy" if (connectivity and authentication and tenant_verified) else "unhealthy"
        
        return HealthCheckResult(
            status=status,
            authentication=authentication,
            tenant_verified=tenant_verified,
            connectivity=connectivity,
            latency_ms=round(latency, 2),
            api_version=api_version,
            details=details,
        )
