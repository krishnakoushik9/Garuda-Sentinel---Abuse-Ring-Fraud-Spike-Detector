"""Cognee Cloud Status CLI Tool.

Enables query of Cognee Cloud connection and tenancy status from command line:
python -m backend.tools.cognee_status
"""

import asyncio
import sys
import logging
from backend.services.cognee import CogneeService, CogneeException

# Configure clean console logging for the CLI tool
logging.basicConfig(level=logging.WARNING, format="%(message)s")

async def main():
    service = CogneeService()
    
    print("\033[1;36m==================================================")
    print("           COGNEE CLOUD INTEGRATION STATUS")
    print("==================================================\033[0m")
    
    try:
        # Run health check diagnostics
        health = await service.health_check()
        connection_status = "\033[1;32mCONNECTED\033[0m" if health.connectivity else "\033[1;31mOFFLINE\033[0m"
        health_status = "\033[1;32mHEALTHY\033[0m" if health.status == "healthy" else "\033[1;31mUNHEALTHY\033[0m"
        auth_status = "\033[1;32mVERIFIED\033[0m" if health.authentication else "\033[1;31mFAILED\033[0m"
        tenant_status = "\033[1;32mVERIFIED\033[0m" if health.tenant_verified else "\033[1;31mUNMATCHED\033[0m"
        
        print(f"Connection Status:  {connection_status}")
        print(f"Health Status:      {health_status}")
        print(f"Authentication:     {auth_status}")
        print(f"Tenant Match:       {tenant_status}")
        print(f"API Version:        {health.api_version}")
        print(f"Latency:            {health.latency_ms:.2f} ms")
        if health.details.get("mock_mode"):
            print("Mode:               \033[1;33mMOCK SANDBOX\033[0m")
        else:
            print("Mode:               \033[1;32mPRODUCTION CLOUD\033[0m")
            
        print("\033[1;34m--------------------------------------------------\033[0m")
        
        # Query Tenant Details
        try:
            tenant = await service.get_current_tenant()
            print(f"Tenant Name:        {tenant.name}")
            print(f"Tenant ID:          {tenant.tenant_id}")
            print(f"User ID:            {tenant.user_id}")
        except Exception as e:
            print(f"\033[1;31mFailed to load Tenant details: {e}\033[0m")
            
        print("\033[1;34m--------------------------------------------------\033[0m")
        
        # Query Subscription Details
        try:
            sub = await service.get_subscription_status()
            print(f"Subscription Plan:  {sub.plan_name}")
            print(f"Plan Status:        {sub.status}")
            print(f"Quota Limit:        {sub.quota_limit:,} requests")
            print(f"Quota Used:         {sub.quota_used:,} requests")
            if sub.expires_at:
                print(f"Expires/Renews:     {sub.expires_at}")
        except Exception as e:
            print(f"\033[1;31mFailed to load Subscription status: {e}\033[0m")
            
        print("\033[1;34m--------------------------------------------------\033[0m")
        
        # Query Billing Details
        try:
            billing = await service.get_billing()
            print(f"Credits Remaining:  ${billing.credits_remaining:.2f} {billing.currency}")
            print(f"Current Balance:    ${billing.balance:.2f} {billing.currency}")
            print(f"Monthly Price:      ${billing.subscription_price:.2f} {billing.currency}")
            if billing.payment_method:
                print(f"Payment Method:     {billing.payment_method}")
        except Exception as e:
            print(f"\033[1;31mFailed to load Billing details: {e}\033[0m")
            
        print("\033[1;36m==================================================\033[0m")
        
        # Exit with status code
        if health.status == "healthy":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except CogneeException as ce:
        print(f"\033[1;31mError querying Cognee: {ce.message} (Status: {ce.status_code})\033[0m")
        print("\033[1;36m==================================================\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\033[1;31mUnexpected error running CLI check: {e}\033[0m")
        print("\033[1;36m==================================================\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
