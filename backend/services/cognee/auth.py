"""Authentication utilities for Cognee Cloud API."""

from typing import Dict
from backend.config.cognee import CogneeSettings

def get_auth_headers(api_key: str = None, tenant_id: str = None) -> Dict[str, str]:
    """Builds standard headers for Cognee Cloud API authentication.
    
    If credentials are not supplied, reads them from CogneeSettings.
    """
    key = api_key or CogneeSettings.COGNEE_API_KEY
    tenant = tenant_id or CogneeSettings.COGNEE_TENANT_ID
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    if key:
        headers["X-Api-Key"] = key
    if tenant:
        headers["X-Tenant-Id"] = tenant
        
    return headers
