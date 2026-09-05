# BOI Banking Ecosystem Simulator

This project is now Phase 2 graph-first synthetic banking ecosystem simulator for PS2 mule-account detection research. The original COBOL prototype remains in `cobol/`; the primary research dataset generator is `backend/ecosystem.py` and the main entrypoint is `./guard.sh`.

## Layout

- `backend/ecosystem.py` - graph-first behavior, fraud, mule, export, Neo4j, and CLI stream engine
- `cobol/` - retained GnuCOBOL prototype and C SQLite bridge
- `database/` - SQLite schema and generated `ecosystem.db`
- `backend/` - Python REST controller
- `frontend/` - web dashboard
- `scripts/` - install, build, run, and reset helpers
- `docs/` - project documentation
- `exports/` - append-only model-facing CSV exports and ground-truth labels

## Ubuntu Setup

```bash
./guard.sh
```

Optional dashboard:

```bash
scripts/run_dashboard.sh
```

Open `http://127.0.0.1:8000`.

## API

- `POST /api/start?accounts=100000&transactions=1000000&speed=100x`
- `POST /api/stop`
- `GET /api/metrics`
- `GET /api/status`

## Phase 2 Engine Behavior

The engine creates up to 100,000 accounts with realistic profile fields, relationship clusters, simulated time, staged activation, behavior-driven transactions, synthetic mule networks, synthetic fraud campaigns, graph analytics, Neo4j updates, and append-only CSV exports.

Model-facing `transactions.csv` and the `transactions` table do not include `mule_flag` or `fraud_flag`. Ground truth is isolated in `mule_labels.csv` and `fraud_labels.csv`.

Generated relationship clusters:

- Family
- Friends
- Employer
- Merchant/customer
- Local geography

Mule network patterns:

- Relay
- Fan-out
- Layering
- Cash-out
- Fraud rings

Fraud campaign patterns:

- Dormancy break
- Rapid in/out
- Velocity spike
- Night activity
- Structured splitting
- Synthetic scam campaigns

## Exports

- `exports/accounts.csv`
- `exports/transactions.csv`
- `exports/relationships.csv`
- `exports/mule_labels.csv`
- `exports/fraud_labels.csv`

## Environment Variables

```bash
BOI_ACCOUNTS=100000 \
BOI_TRANSACTIONS=1000000 \
BOI_SPEED=100x \
BOI_SEED=20260101 \
./guard.sh
```

Neo4j is optional and enabled with:

```bash
NEO4J_ENABLED=1 \
NEO4J_URL=http://localhost:7474 \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=password \
./guard.sh
```
