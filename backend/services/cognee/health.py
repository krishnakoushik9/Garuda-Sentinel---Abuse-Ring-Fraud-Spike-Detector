"""Diagnostic Health Utilities for Cognee Cloud Integration."""

import logging
from typing import Dict, Any

from .service import CogneeService
from .models import HealthCheckResult

logger = logging.getLogger("cognee.health")

async def run_diagnostics(service: CogneeService = None) -> Dict[str, Any]:
    """Runs a complete set of diagnostic checks and returns raw details.
    
    Checks environment config, DNS/network, authentication, and tenant validity.
    """
    srv = service or CogneeService()
    
    # Check config validity first
    config_valid = True
    config_error = None
    try:
        from backend.config.cognee import CogneeSettings
        CogneeSettings.validate()
    except ValueError as val_err:
        config_valid = False
        config_error = str(val_err)
        
    if not config_valid:
        return {
            "status": "unhealthy",
            "diagnostics": {
                "config_valid": False,
                "config_error": config_error,
                "api_reachable": False,
                "authenticated": False,
                "tenant_verified": False,
                "latency_ms": 0.0,
            }
        }
        
    health_result: HealthCheckResult = await srv.health_check()
    
    return {
        "status": health_result.status,
        "diagnostics": {
            "config_valid": True,
            "api_reachable": health_result.connectivity,
            "authenticated": health_result.authentication,
            "tenant_verified": health_result.tenant_verified,
            "latency_ms": health_result.latency_ms,
            "api_version": health_result.api_version,
            "mock_mode": health_result.details.get("mock_mode", False),
            "details": health_result.details,
        }
    }
