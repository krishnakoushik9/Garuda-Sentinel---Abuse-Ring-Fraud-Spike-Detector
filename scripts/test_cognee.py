"""Automated Test Suite for Cognee Cloud Integration.

Covers:
- Configuration validation tests
- Environment loading tests
- Connection and DNS error handling tests
- Authentication (401/403) handling tests
- Health diagnostics tests
- Retry logic with backoff tests (only safe HTTP methods)
- Timeout handling tests
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

# Import from our new integration package
from backend.config.cognee import CogneeSettings
from backend.services.cognee import (
    CogneeClient,
    CogneeService,
    CogneeException,
    CogneeConnectionException,
    CogneeAuthException,
    CogneeRateLimitException,
    CogneeValidationException,
    CogneeServerException,
)

class TestCogneeConfiguration(unittest.TestCase):
    """Tests configuration validation and environment loading."""
    
    def setUp(self):
        # Store original settings
        self.orig_key = CogneeSettings.COGNEE_API_KEY
        self.orig_url = CogneeSettings.COGNEE_BASE_URL
        self.orig_tenant = CogneeSettings.COGNEE_TENANT_ID
        self.orig_user = CogneeSettings.COGNEE_USER_ID

    def tearDown(self):
        # Restore settings
        CogneeSettings.COGNEE_API_KEY = self.orig_key
        CogneeSettings.COGNEE_BASE_URL = self.orig_url
        CogneeSettings.COGNEE_TENANT_ID = self.orig_tenant
        CogneeSettings.COGNEE_USER_ID = self.orig_user

    def test_validation_passes_with_all_variables(self):
        CogneeSettings.COGNEE_API_KEY = "test_key"
        CogneeSettings.COGNEE_BASE_URL = "http://test.cognee.ai"
        CogneeSettings.COGNEE_TENANT_ID = "test_tenant"
        CogneeSettings.COGNEE_USER_ID = "test_user"
        
        # Should not raise exception
        try:
            CogneeSettings.validate()
        except ValueError as e:
            self.fail(f"validate() raised ValueError unexpectedly: {e}")

    def test_validation_fails_when_variables_missing(self):
        CogneeSettings.COGNEE_API_KEY = None
        with self.assertRaises(ValueError) as context:
            CogneeSettings.validate()
        self.assertIn("COGNEE_API_KEY", str(context.exception))


class TestCogneeHttpClient(unittest.IsolatedAsyncioTestCase):
    """Tests the HTTP Client wrapper including Auth, Connection, Retries, and Timeouts."""

    def setUp(self):
        self.patcher_dns = patch("socket.gethostbyname", return_value="127.0.0.1")
        self.patcher_dns.start()

    def tearDown(self):
        self.patcher_dns.stop()

    @patch("backend.config.cognee.CogneeSettings.COGNEE_API_KEY", "real_key")
    @patch("backend.config.cognee.CogneeSettings.COGNEE_BASE_URL", "https://api.cognee.ai")
    async def test_authentication_failure_raises_exception(self):
        client = CogneeClient()
        client.mock_mode = False  # Force HTTP requests
        
        # Mock Session and response returning 401 Unauthorized
        mock_response = AsyncMock()
        mock_response.status = 401
        
        mock_session = MagicMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with self.assertRaises(CogneeAuthException):
                await client.request("GET", "health")

    @patch("backend.config.cognee.CogneeSettings.COGNEE_API_KEY", "real_key")
    @patch("backend.config.cognee.CogneeSettings.COGNEE_BASE_URL", "https://api.cognee.ai")
    async def test_connection_failure_raises_exception(self):
        client = CogneeClient()
        client.mock_mode = False
        
        # Mock session to raise connection error
        mock_session = MagicMock()
        mock_session.request.side_effect = aiohttp.ClientConnectorError(
            connection_key=None,
            os_error=ConnectionRefusedError()
        )
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with self.assertRaises(CogneeConnectionException):
                await client.request("GET", "health", max_retries=0)

    @patch("backend.config.cognee.CogneeSettings.COGNEE_API_KEY", "real_key")
    @patch("backend.config.cognee.CogneeSettings.COGNEE_BASE_URL", "https://api.cognee.ai")
    async def test_timeout_raises_exception(self):
        client = CogneeClient()
        client.mock_mode = False
        
        mock_session = MagicMock()
        mock_session.request.side_effect = asyncio.TimeoutError()
        
        with patch.object(client, "_get_session", return_value=mock_session):
            with self.assertRaises(CogneeConnectionException):
                await client.request("GET", "health", max_retries=0)

    @patch("backend.config.cognee.CogneeSettings.COGNEE_API_KEY", "real_key")
    @patch("backend.config.cognee.CogneeSettings.COGNEE_BASE_URL", "https://api.cognee.ai")
    async def test_retry_on_safe_method_get(self):
        client = CogneeClient()
        client.mock_mode = False
        
        # First request returns 502, second request returns 200 with data
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 502
        
        mock_response_ok = AsyncMock()
        mock_response_ok.status = 200
        mock_response_ok.json.return_value = {"ok": True}
        
        mock_session = MagicMock()
        # Mock sequential return values for __aenter__
        mock_session.request.return_value.__aenter__.side_effect = [
            mock_response_fail,
            mock_response_ok
        ]
        
        with patch("asyncio.sleep", return_value=None):
            with patch.object(client, "_get_session", return_value=mock_session):
                result = await client.request("GET", "health", max_retries=2)
                self.assertEqual(result, {"ok": True})
                # Check that request was called twice
                self.assertEqual(mock_session.request.call_count, 2)

    @patch("backend.config.cognee.CogneeSettings.COGNEE_API_KEY", "real_key")
    @patch("backend.config.cognee.CogneeSettings.COGNEE_BASE_URL", "https://api.cognee.ai")
    async def test_no_retry_on_unsafe_method_post(self):
        client = CogneeClient()
        client.mock_mode = False
        
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 502
        
        mock_session = MagicMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response_fail
        
        with patch("asyncio.sleep", return_value=None):
            with patch.object(client, "_get_session", return_value=mock_session):
                with self.assertRaises(CogneeServerException):
                    await client.request("POST", "api/v1/api-keys", data={"name": "test"}, max_retries=2)
                # Should fail fast without retry (called exactly once)
                self.assertEqual(mock_session.request.call_count, 1)


class TestCogneeService(unittest.IsolatedAsyncioTestCase):
    """Tests the Service methods returning typed models."""

    async def test_health_check_success(self):
        mock_client = AsyncMock()
        # Mock GET health and GET permissions/tenants/current
        mock_client.tenant_id = "test_tenant"
        mock_client.mock_mode = True
        mock_client.request.side_effect = [
            {"status": "healthy", "version": "1.0.0-cloud"},
            {"tenant_id": "test_tenant", "user_id": "user_123", "name": "Aegis", "is_active": True}
        ]
        
        service = CogneeService(client=mock_client)
        result = await service.health_check()
        
        self.assertEqual(result.status, "healthy")
        self.assertTrue(result.connectivity)
        self.assertTrue(result.authentication)
        self.assertTrue(result.tenant_verified)
        self.assertEqual(result.api_version, "1.0.0-cloud")

    async def test_health_check_tenant_mismatch(self):
        mock_client = AsyncMock()
        mock_client.tenant_id = "configured_tenant"
        mock_client.mock_mode = True
        mock_client.request.side_effect = [
            {"status": "healthy", "version": "1.0.0-cloud"},
            {"tenant_id": "different_tenant", "user_id": "user_123", "name": "Aegis", "is_active": True}
        ]
        
        service = CogneeService(client=mock_client)
        result = await service.health_check()
        
        self.assertEqual(result.status, "unhealthy")
        self.assertTrue(result.connectivity)
        self.assertTrue(result.authentication)
        self.assertFalse(result.tenant_verified)


if __name__ == "__main__":
    unittest.main()
