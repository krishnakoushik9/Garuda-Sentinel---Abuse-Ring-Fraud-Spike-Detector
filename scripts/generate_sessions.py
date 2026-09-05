#!/usr/bin/env python3
import asyncio
import os
import sys
import logging
from backend.config.cognee import CogneeSettings
import cognee

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_sessions")

CONCURRENCY_LIMIT = 3

async def run_agent_session(session_idx: int, sem: asyncio.Semaphore):
    async with sem:
        session_id = f"aegis_agent_session_{session_idx:03d}"
        
        obs = f"Aegis Sentinel Fraud Agent observation: community COM-{session_idx} displays high LSTM sequence anomaly score. Inflow is distributed dynamically."
        query = f"COM-{session_idx} historical fraud pattern matching"
        verdict = f"Aegis Agent Verdict: freeze cluster nodes for COM-{session_idx} due to high GNN propagation risk."
        
        for attempt in range(3):
            try:
                # 1. Remember observation
                await cognee.remember(obs, dataset_name="fraud_investigations", session_id=session_id)
                # 2. Search past memory
                await cognee.search(query, dataset_name="fraud_investigations", session_id=session_id)
                # 3. Remember verdict
                await cognee.remember(verdict, dataset_name="fraud_investigations", session_id=session_id)
                
                logger.info(f"Successfully completed agent turns for {session_id}")
                # Add a sleep to prevent hitting rate limits
                await asyncio.sleep(1.5)
                return True
            except Exception as e:
                logger.warning(f"Error logging agent session {session_id} (Attempt {attempt+1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(3 ** attempt)
        logger.error(f"Failed to log agent session {session_id} after retries.")
        return False

async def main():
    logger.info("Initializing Cognee connection...")
    try:
        CogneeSettings.validate()
        await cognee.serve(
            url=CogneeSettings.COGNEE_BASE_URL,
            api_key=CogneeSettings.COGNEE_API_KEY
        )
        logger.info("Cognee connection established.")
    except Exception as e:
        logger.error(f"Failed to initialize Cognee connection: {e}")
        sys.exit(1)

    logger.info("Starting generation of another 45 multi-turn agent sessions sequentially/in small batches...")
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # We will log 45 sessions: from 201 to 245
    tasks = [run_agent_session(i, sem) for i in range(201, 246)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r)
    logger.info(f"Agent session generation complete. Successful sessions: {success_count}/45")

if __name__ == "__main__":
    asyncio.run(main())
