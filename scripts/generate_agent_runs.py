#!/usr/bin/env python3
import asyncio
import os
import sys
import logging
from backend.config.cognee import CogneeSettings
import cognee

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_agent_runs")

CONCURRENCY_LIMIT = 5

def make_agent_run(session_idx: int):
    session_id = f"agent_session_id_{session_idx:02d}"
    session_name = f"AegisFraudAgent_{session_idx:02d}"

    # Factory-defined decorated agent entrypoint
    # We omit dataset_name so Cognee handles the user's default scoped dataset permissions automatically.
    @cognee.agent_memory(
        agent_session_name=session_name,
        session_id=session_id,
        dataset_name="fraud_investigations",
        with_memory=True,
        with_session_memory=True,
        save_session_traces=True
    )
    async def run_agent(community_id: str):
        logger.info(f"Agent {session_name} executing memory search/write for {community_id}...")
        # Log a memory observation
        await cognee.remember(
            f"Forensic observation logged by {session_name} for {community_id}: Suspicious fan-out layering loops detected.",
            dataset_name="fraud_investigations",
            session_id=session_id
        )
        return f"Verdict: High Risk flagged for {community_id}"

    return run_agent, session_id

async def run_simulated_agent(session_idx: int, sem: asyncio.Semaphore):
    async with sem:
        agent_fn, session_id = make_agent_run(session_idx)
        community_id = f"COM-{300 + session_idx}"
        
        for attempt in range(3):
            try:
                # Execute the decorated agent function
                verdict = await agent_fn(community_id)
                logger.info(f"Successfully finished Agent run #{session_idx} ({session_id}) -> {verdict}")
                return True
            except Exception as e:
                logger.warning(f"Error executing agent run #{session_idx} (Attempt {attempt+1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        logger.error(f"Failed agent run #{session_idx} after retries.")
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

    logger.info("Sequential setup step to initialize default user database records and avoid SQLite uniqueness race conditions...")
    try:
        # A simple remember call to trigger default user creation
        await cognee.remember("Initialization ping", dataset_name="fraud_investigations", session_id="init_ping_session")
        logger.info("Database user initialization success.")
    except Exception as e:
        logger.warning(f"Database user initialization warning: {e}")

    logger.info("Starting generation of 45 decorated agent memory runs...")
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    tasks = [run_simulated_agent(i, sem) for i in range(1, 46)]
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if r)
    logger.info(f"Completed agent memory runs. Successful agent runs: {success_count}/45")

    # Let's also run another 45 pure session memory logs using cognee.remember
    # to fulfill the user's request for "send another 40 sessions again"
    logger.info("Sending another 45 session memory records using cognee.remember...")
    
    async def log_pure_session(idx: int):
        session_id = f"extra_session_{idx:02d}"
        content = f"Simulated Session Run #{idx}: Checking forensic compliance indexes. Audit passed."
        try:
            await cognee.remember(content, dataset_name="fraud_investigations", session_id=session_id)
            logger.info(f"Successfully logged extra session memory for {session_id}")
            return True
        except Exception as e:
            logger.warning(f"Error logging extra session {session_id}: {e}")
            return False

    pure_tasks = [log_pure_session(i) for i in range(1, 46)]
    pure_results = await asyncio.gather(*pure_tasks)
    pure_success = sum(1 for r in pure_results if r)
    logger.info(f"Extra sessions generation complete: {pure_success}/45")

if __name__ == "__main__":
    asyncio.run(main())
