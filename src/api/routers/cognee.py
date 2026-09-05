"""FastAPI Router for Cognee Cloud Integration."""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Dict, Any

from backend.services.cognee import CogneeService, HealthCheckResult, TenantInfo, SubscriptionStatus, BillingInfo, ApiKeyInfo, ApiKeyCreateResponse
from backend.services.cognee.exceptions import CogneeException

router = APIRouter(prefix="/internal/cognee", tags=["Cognee Integration"])
service = CogneeService()

@router.get("/health", response_model=HealthCheckResult)
async def get_cognee_health():
    """Diagnostic health check verifying connectivity, credentials, latency, and tenancy details."""
    try:
        health_report = await service.health_check()
        return health_report
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cognee Health Check failed: {ce.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error running Cognee diagnostics: {str(e)}"
        )

@router.get("/tenant", response_model=TenantInfo)
async def get_tenant_details():
    """Retrieve details of the active workspace tenant."""
    try:
        return await service.get_current_tenant()
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )

@router.get("/subscription", response_model=SubscriptionStatus)
async def get_subscription_status():
    """Retrieve active subscription plan details and quotas."""
    try:
        return await service.get_subscription_status()
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )

@router.get("/billing", response_model=BillingInfo)
async def get_billing_details():
    """Retrieve credit balances and billing statement summaries."""
    try:
        return await service.get_billing()
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )

@router.get("/api-keys", response_model=List[ApiKeyInfo])
async def list_cognee_api_keys():
    """List active API keys created for the workspace."""
    try:
        return await service.list_api_keys()
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )

@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_cognee_api_key(name: str = Query(..., description="Friendly name for the API key")):
    """Generate a new API key for the current tenant workspace."""
    try:
        return await service.create_api_key(name)
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_200_OK)
async def delete_cognee_api_key(key_id: str):
    """Delete an API key by its unique ID identifier."""
    try:
        await service.delete_api_key(key_id)
        return {"status": "success", "message": f"API key {key_id} deleted successfully."}
    except CogneeException as ce:
        raise HTTPException(
            status_code=ce.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ce.message
        )
