# PS2 Fraud Intelligence Platform - System Inventory

## COBOL Layer
- **Files found:**
  - `cobol/banking_engine.cob`: Core transaction simulation engine. Uses GnuCOBOL.
  - `cobol/sqlite_bridge.c`: C bridge allowing COBOL to communicate with SQLite.
- **What each does:**
  - `banking_engine.cob`: Generates synthetic accounts and transactions. Implements complex mule network patterns (fan-out, relay, layering) and fraud patterns (dormancy break, rapid in/out, velocity spike).
  - `sqlite_bridge.c`: Provides high-performance SQLite bindings for COBOL, including transaction batching (BEGIN/COMMIT) and specialized INSERT functions for accounts, transactions, and fraud events.
- **Transaction types handled:**
  - `UPI`, `IMPS`, `SALARY`, `MERCHANT`, `NEFT`, `TRANSFER`.
- **Data structures defined:**
  - `WS-ACCOUNT-STATE`: In-memory tracking of balances and statuses for up to 100,000 accounts.
  - `WS-STRINGS`: Buffers for SQL data fields (Account IDs, Transaction IDs, Timestamps, etc.).
  - `WS-CONFIG`: Environment-driven simulation parameters.

## Existing Python Code
- **Files found:**
  - `backend/ecosystem.py`: Advanced graph-first synthetic data generator.
  - `backend/server.py`: Read-only dashboard API server (Python `ThreadingHTTPServer`).
- **What each does:**
  - `ecosystem.py`: Generates a realistic banking ecosystem with social relationships (family, friend, merchant, etc.), behavioral transaction modeling based on customer segments (student, employee, business), and multi-layer mule network seeding. Includes a Neo4j sink for graph population.
  - `server.py`: Provides a REST API (`/api/metrics`, `/api/status`) that reads from the SQLite database to power the frontend dashboard.

## Database State
- **SQLite:** 
  - `database/ecosystem.db`: Primary database for the Python ecosystem simulation.
  - `database/banking.db`: Database for the COBOL simulation.
  - **Schema:** Defined in `database/schema.sql`. Includes tables for `accounts`, `transactions`, `account_relationships`, `mule_networks`, `fraud_events`, and `graph_analytics`.
  - **Row Counts:** Currently contains thousands of seeded accounts and transactions (verified via `exports/` CSVs).
- **Neo4j:**
  - **Connection Config:** Found in `backend/ecosystem.py` (defaults to `http://localhost:7474`).
  - **Seed Data:** Neo4j population logic is integrated into `ecosystem.py`, pushing nodes (Accounts) and edges (Transactions/SENT_TO).

## Shell Scripts / Entrypoints
- `guard.sh`: Main entry point for the Python ecosystem simulation. Sets environment variables and runs `ecosystem.py`.
- `scripts/build.sh`: Compiles the COBOL engine and C bridge into the `build/boi_banking_engine` executable.
- `scripts/run_dashboard.sh`: Starts the Python API server for the web dashboard.
- `scripts/install_ubuntu.sh`: Setup script for GnuCOBOL and SQLite dependencies.
- `scripts/reset_database.sh`: Cleans up existing database files and exports.

## What Is MISSING (gaps to fill)
- **Kafka producer/consumer:** No code exists for real-time transaction streaming via Kafka.
- **FastAPI middleware layer:** The current API is a simple `http.server`; a robust FastAPI layer for LangGraph integration is missing.
- **ML models:** No code found for:
  - XGBoost (Tabular Fraud Detection)
  - GraphSAGE (GNN for Mule Detection)
  - LSTM Autoencoder (Anomalous Sequence Detection)
- **LangGraph agents:** No existing implementation of LLM-powered investigation agents.
- **Frontend (advanced):**
  - **Marketing Page:** Not found.
  - **Analyst Dashboard:** Current `frontend/index.html` is a basic simulation monitor, not a full-featured fraud investigation platform.

## Recommended Build Order
1. **Infrastructure:** Set up Kafka and link `ecosystem.py` or `banking_engine.cob` to produce real-time streams.
2. **Middleware:** Rebuild the backend using FastAPI to support async processing and agentic workflows.
3. **Graph Layer:** Ensure Neo4j is fully populated and integrated with the new FastAPI layer.
4. **ML Pipeline:** Implement the detection models (XGBoost/GraphSAGE) and expose them via the middleware.
5. **Agentic Layer:** Integrate LangGraph for automated fraud narrative generation.
6. **Frontend Expansion:** Build the comprehensive Analyst Dashboard and Marketing Page.
