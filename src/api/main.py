from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from src.api.routers import transactions, accounts, investigations, alerts, graph, dashboard, regulatory, mule_intelligence, cross_channel, datasource, settings, fraud_agent, cobol_sentinel, swap, cognee
from src.api import ws
from src.api.deps import get_db, get_neo4j, get_redis
from src.system import startup_init

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Log connection status
    logger.info("Starting up PS2 Fraud Intelligence API...")
    
    # Cognee Cloud Startup Verification (Fail Fast)
    try:
        logger.info("Verifying Cognee Cloud Integration status...")
        from backend.config.cognee import CogneeSettings
        from backend.services.cognee import CogneeService
        
        # 1. Validate environment variables
        CogneeSettings.validate()
        logger.info("Cognee Cloud settings validated.")

        # Initialize standard SDK to point to Cognee Cloud tenant
        import cognee
        logger.info(f"Initializing Cognee SDK to serve at: {CogneeSettings.COGNEE_BASE_URL}")
        try:
            await cognee.serve(
                url=CogneeSettings.COGNEE_BASE_URL,
                api_key=CogneeSettings.COGNEE_API_KEY
            )
            logger.info("Cognee SDK serve initialized successfully.")
        except Exception as sdk_err:
            logger.warning(f"Cognee SDK serve local config failed (might be offline): {sdk_err}")
        
        # 2. Verify API connection and authentication
        cognee_service = CogneeService()
        connection_ok = await cognee_service.verify_connection()
        if not connection_ok:
            logger.error("Failed to connect or authenticate with Cognee Cloud.")
            raise RuntimeError("Cognee Cloud connectivity / authentication check failed.")
            
        health_check_res = await cognee_service.health_check()
        if health_check_res.status != "healthy":
            logger.error(f"Cognee health check status: {health_check_res.status}")
            raise RuntimeError("Cognee health check status is unhealthy.")
            
        logger.info("Cognee Cloud Integration verified successfully.")
    except Exception as e:
        logger.warning(f"Cognee Integration startup verification failed: {e}")
        logger.warning("Continuing startup in Resilient Offline Mode.")
    
    # Initialize Aggressive Swap Management System with selective RAM protection
    try:
        logger.info("Initializing Swap Manager System...")
        startup_init()
        logger.info("Swap Manager System successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Swap Manager System: {e}")
    
    # Check SQLite
    try:
        db_gen = get_db()
        db = next(db_gen)
        db.execute("SELECT 1")
        logger.info("SQLite: Connected")
    except Exception as e:
        logger.error(f"SQLite: Failed ({e})")
        
    # Check Neo4j
    try:
        driver_gen = get_neo4j()
        driver = next(driver_gen)
        if driver:
            logger.info("Neo4j: Connected")
        else:
            logger.warning("Neo4j: Offline")
    except Exception:
        logger.warning("Neo4j: Offline")
        
    # Check Redis
    try:
        r_gen = get_redis()
        r = next(r_gen)
        if r:
            logger.info("Redis: Connected")
        else:
            logger.warning("Redis: Offline")
    except Exception:
        logger.warning("Redis: Offline")

    # Start government data ingestion scheduler and warm empty tables.
    try:
        regulatory.govdata_injector.start_scheduler()
        await regulatory.govdata_injector.ingest_all_if_empty()
        logger.info("GovData: Scheduler initialized")
    except Exception as e:
        logger.warning(f"GovData: Startup initialization skipped ({e})")

    yield
    # Shutdown
    try:
        regulatory.govdata_injector.shutdown_scheduler()
    except Exception as e:
        logger.warning(f"GovData: Scheduler shutdown skipped ({e})")
    logger.info("Shutting down API...")

app = FastAPI(
    title="PS2 Fraud Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(investigations.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(regulatory.router, prefix="/api/v1")
app.include_router(regulatory.govdata_router, prefix="/api/v1")
app.include_router(mule_intelligence.router, prefix="/api/v1")
app.include_router(cross_channel.router, prefix="/api/v1")
app.include_router(fraud_agent.router, prefix="/api/v1")
app.include_router(cobol_sentinel.router, prefix="/api/v1")
app.include_router(datasource.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api")
app.include_router(swap.router, prefix="/api/v1")
app.include_router(cognee.router)  # Register without prefix to support /internal/cognee/health
app.include_router(ws.router)

from src.api.routers import fraud_models
app.include_router(fraud_models.router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "fraud-intelligence-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
