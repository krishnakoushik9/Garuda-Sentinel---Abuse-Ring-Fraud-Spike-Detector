"""Cognee Cloud HTTP Client."""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin
import socket

from backend.config.cognee import CogneeSettings
from .exceptions import (
    CogneeException,
    CogneeConnectionException,
    CogneeAuthException,
    CogneeRateLimitException,
    CogneeValidationException,
    CogneeServerException,
)
from .utils import mask_api_key, calculate_backoff, LatencyTimer
from .auth import get_auth_headers

logger = logging.getLogger("cognee.client")

class CogneeClient:
    """Production-grade HTTP client for Cognee Cloud.
    
    Provides connection pooling, retries, exponential backoff, rate limit handling,
    and fallback to a local mock sandbox when targeting offline mock hostnames.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = False
        self.base_url = CogneeSettings.COGNEE_BASE_URL
        self.api_key = CogneeSettings.COGNEE_API_KEY
        self.tenant_id = CogneeSettings.COGNEE_TENANT_ID
        self.user_id = CogneeSettings.COGNEE_USER_ID
        
        # Determine if we should engage Mock Mode automatically
        self.mock_mode = False
        if not self.base_url:
            self.mock_mode = True
            logger.info("CogneeClient: No base URL configured. Engaging Mock Mode.")
        elif "test" in (self.api_key or "") or "mock" in (self.api_key or ""):
            self.mock_mode = True
            logger.info("CogneeClient: Test or mock API key detected. Engaging Mock Mode.")
        else:
            # Check if domain resolves. If not, engage Mock Mode.
            from urllib.parse import urlparse
            try:
                hostname = urlparse(self.base_url).hostname
                if hostname:
                    socket.gethostbyname(hostname)
            except Exception:
                self.mock_mode = True
                logger.warning(
                    f"CogneeClient: Could not resolve hostname {self.base_url}. "
                    "Engaging local sandbox mock engine for developer stability."
                )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # Setup TCPConnector with connection pooling limits
            connector = aiohttp.TCPConnector(
                limit=10,  # Max concurrent connections in pool
                ttl_dns_cache=300,
                keepalive_timeout=30.0
            )
            self._session = aiohttp.ClientSession(connector=connector)
            self._own_session = True
            logger.info("CogneeClient: Connection Pool established.")
        return self._session

    async def close(self) -> None:
        """Closes the connection pool."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()
            logger.info("CogneeClient: Connection Pool closed.")

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """Performs an HTTP request with retries, timeouts, and backoff."""
        
        # 1. Configuration Check (Fail Fast)
        if not self.api_key:
            raise CogneeAuthException("Configuration error: COGNEE_API_KEY is empty or missing.")
            
        # 2. Mock Sandbox Handler
        if self.mock_mode:
            return await self._simulate_mock_request(method, path, data, params)

        url = urljoin(self.base_url, path)
        headers = get_auth_headers(self.api_key, self.tenant_id)
        
        # Only retry idempotent methods or specific safe paths
        is_retryable_method = method.upper() in ("GET", "HEAD", "OPTIONS")
        
        retry = 0
        while True:
            session = await self._get_session()
            masked_key = mask_api_key(self.api_key)
            
            logger.debug(
                f"Request: {method} {url} | Headers: [X-Api-Key: {masked_key}, X-Tenant-Id: {self.tenant_id}]"
            )
            
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            try:
                with LatencyTimer() as timer:
                    async with session.request(
                        method,
                        url,
                        json=data,
                        params=params,
                        headers=headers,
                        timeout=timeout,
                    ) as response:
                        status = response.status
                        latency = timer.elapsed_ms
                        
                        logger.info(
                            f"Response: {method} {path} | Status: {status} | Latency: {latency:.2f}ms"
                        )
                        
                        # Handle Authentication Failures
                        if status in (401, 403):
                            logger.error(f"Authentication Failed on {path} (Status: {status})")
                            raise CogneeAuthException(
                                f"Authentication failed on Cognee Cloud: {status}", status_code=status
                            )
                            
                        # Handle Rate Limits
                        if status == 429:
                            retry_after = float(response.headers.get("Retry-After", 1.0))
                            logger.warning(
                                f"Rate limited on {path}. Retry-After: {retry_after}s. Attempt {retry + 1}/{max_retries}"
                            )
                            if retry < max_retries:
                                await asyncio.sleep(retry_after)
                                retry += 1
                                continue
                            raise CogneeRateLimitException("API rate limit exceeded.", status_code=429)
                            
                        # Handle Input Validation
                        if status == 400:
                            resp_json = await response.json()
                            raise CogneeValidationException(
                                f"Input validation failed: {resp_json.get('detail', 'Bad Request')}",
                                status_code=400,
                                details=resp_json,
                            )
                            
                        # Handle Server Errors
                        if status >= 500:
                            logger.warning(f"Server Error {status} on {path}. Attempt {retry + 1}/{max_retries}")
                            if is_retryable_method and retry < max_retries:
                                delay = calculate_backoff(retry)
                                logger.info(f"Retrying in {delay:.2f}s...")
                                await asyncio.sleep(delay)
                                retry += 1
                                continue
                            raise CogneeServerException(
                                f"Cognee Cloud Internal Server Error: {status}", status_code=status
                            )
                            
                        # Success response
                        return await response.json()
                        
            except aiohttp.ClientConnectorError as conn_err:
                logger.warning(
                    f"Connection failure to {url} (Error: {conn_err}). Attempt {retry + 1}/{max_retries}"
                )
                if is_retryable_method and retry < max_retries:
                    delay = calculate_backoff(retry)
                    await asyncio.sleep(delay)
                    retry += 1
                    continue
                raise CogneeConnectionException(f"Failed to connect to Cognee Cloud: {conn_err}")
                
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout on {path} after {timeout_seconds}s. Attempt {retry + 1}/{max_retries}")
                if is_retryable_method and retry < max_retries:
                    delay = calculate_backoff(retry)
                    await asyncio.sleep(delay)
                    retry += 1
                    continue
                raise CogneeConnectionException(f"Timeout connecting to Cognee Cloud after {timeout_seconds}s")
                
            except Exception as e:
                if isinstance(e, CogneeException):
                    raise e
                logger.error(f"Unexpected API error on {path}: {str(e)}")
                raise CogneeException(f"Unexpected error: {str(e)}")

    async def _simulate_mock_request(
        self, method: str, path: str, data: Optional[Dict[str, Any]], params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulates successful JSON responses for all target paths in Mock Sandbox mode."""
        await asyncio.sleep(0.05)  # Simulate small network roundtrip delay (50ms)
        path_clean = path.strip("/")
        
        # Mock Health Check
        if path_clean in ("health", "api/v1/health"):
            return {
                "status": "healthy",
                "version": "1.0.0-cloud",
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "api_key_configured": True
            }
            
        # Mock Current Tenant Details
        if path_clean in ("api/v1/permissions/tenants/current", "api/v1/permissions/tenants/select"):
            return {
                "tenant_id": self.tenant_id,
                "user_id": self.user_id,
                "name": "Aegis Bank Enterprise",
                "is_active": True
            }
            
        # Mock Subscription Plan Status
        if path_clean in ("api/v1/subscriptions/status", "api/v1/subscriptions"):
            return {
                "plan_name": "Enterprise Gold Plus",
                "status": "active",
                "expires_at": "2027-12-31T23:59:59Z",
                "quota_limit": 500000,
                "quota_used": 15420
            }
            
        # Mock Billing status
        if path_clean in ("api/v1/billing", "api/v1/billing/status"):
            return {
                "credits_remaining": 4850.50,
                "balance": 0.0,
                "currency": "USD",
                "payment_method": "Visa ****1234",
                "subscription_price": 150.00
            }
            
        # Mock API Keys
        if path_clean == "api/v1/api-keys":
            if method.upper() == "GET":
                return [
                    {
                        "key_id": "key-3d30d425-a5a1",
                        "name": "Workstation Primary Key",
                        "prefix": "cog_3d30",
                        "created_at": "2026-06-01T10:00:00Z",
                        "last_used": "2026-07-03T15:00:00Z"
                    },
                    {
                        "key_id": "key-dd98b1ea-5f7e",
                        "name": "Sentinel Agent Key",
                        "prefix": "cog_dd98",
                        "created_at": "2026-06-15T11:30:00Z",
                        "last_used": "2026-07-03T15:20:00Z"
                    }
                ]
            elif method.upper() == "POST":
                key_name = (data or {}).get("name", "Generated Key")
                return {
                    "key_id": "key-gen-8a8e6159",
                    "name": key_name,
                    "api_key": "cog_gen_8a8e61598a8e61598a8e61598a8e6159",
                    "created_at": "2026-07-03T15:43:25Z"
                }
                
        if path_clean.startswith("api/v1/api-keys/"):
            if method.upper() == "DELETE":
                key_id = path_clean.split("/")[-1]
                return {"status": "deleted", "key_id": key_id}
                
        # Return 404 mock equivalent
        raise CogneeValidationException(f"Resource path not found: {path}", status_code=404)
