# API Contract Audit

This document records the exact alignment audit of all API endpoints called by the frontend `app.js` and their FastAPI counterparts in the `src/api` routers. All mismatches have been resolved by aligning the frontend JS structure and query parameters with the python API endpoints, which serve as the source of truth.

---

### Endpoint Mapping & Verification Table

| Frontend Endpoint / Method | Backend Endpoint / Method | Verified Parameters | Verified Response Shape | Status | Fixes Made |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /dashboard/summary` | `GET /api/v1/dashboard/summary` | None | `total_accounts`, `total_transactions`, `high_risk_count`, `mule_count`, `top_fraud_patterns`, `recent_alerts`, `graph_stats` | **MATCH** | Aligned counts, queries, and JOIN metrics to retrieve transactional parameters directly inside alert items. |
| `GET /transactions?limit=20` | `GET /api/v1/transactions` | `limit=20` (FastAPI supports query param) | `List[Transaction]` (each item contains `transaction_id`, `sender_account`, `receiver_account`, `amount`, `channel`, `risk_score`, `timestamp`) | **MATCH** | None needed (fully aligned). |
| `GET /accounts?limit=20` | `GET /api/v1/accounts` | `limit=20` (FastAPI supports query param) | `List[AccountProfile]` (each item contains `account_id`, `name`, `customer_segment`, `city`, `risk_profile`, `pagerank`, `community_id`) | **MATCH** | None needed (fully aligned). |
| `GET /graph/stats` | `GET /api/v1/graph/stats` | None | `total_nodes`, `total_edges`, `total_communities`, `mule_suspected_count`, `is_offline` | **MATCH** | Handled fallback states gracefully for zero-node graph loaders. |
| `GET /graph/fraud-rings` | `GET /api/v1/graph/fraud-rings` | None | `List[Dict]` (with keys `community_id`, `avg_risk`, `size`) | **MATCH** | None needed (fully aligned). |
| `GET /graph/community/{community_id}` | `GET /api/v1/graph/community/{community_id}` | `community_id` (Path variable) | `List[Dict]` (with keys `account_id`, `name`, `risk_profile`, `pagerank`, `propagated_risk_score`) | **MATCH** | Rendered custom node sizing (`propagated_risk_score`) and custom color bands in D3. |
| `POST /investigate?txn_id={id}&account_id=SCANNER` | `POST /api/v1/investigate` | `txn_id`, `account_id` (Query params) | `{"investigation_id": "uuid-str"}` | **MATCH** | Completely aligned query parameters. |
| `GET /investigate/{investigation_id}` | `GET /api/v1/investigate/{investigation_id}` | `investigation_id` (Path variable) | `id`, `account_id`, `status`, `created_at`, `final_verdict`, `final_risk_score`, `explanation_narrative`, `graph_findings`, `shap_values` | **MATCH** | **FIXED MISMATCH**: Frontend initially queried `result.verdict` and `result.explanation`. Aligned to look up `final_verdict` and `explanation_narrative` dynamically, with safe fallbacks. |
| `GET /accounts/{id}` | `GET /api/v1/accounts/{account_id}` | `account_id` (Path variable) | `AccountProfile` (includes `recent_transactions` list) | **MATCH** | Enriched modal UI data displaying segment, PageRank, city, and transactional history. |
| `POST /accounts/{id}/flag` | `POST /api/v1/accounts/{account_id}/flag` | `account_id` (Path variable) | `{"status": "success", "message": "..."}` | **MATCH** | None needed. |
| `GET /alerts/stream` (SSE) | `GET /api/v1/alerts/stream` | None | SSE stream yielding serialized JSON chunks with keys `id`, `transaction_id`, `account_id`, `fraud_type`, `severity`, `timestamp`, `amount`, `risk_score`, `channel` | **MATCH** | **FIXED MISMATCH**: Enriched SSE payload with a SQL `JOIN` on transactions to supply real amounts, scores, and channels instantly to the UI feed. |
| `GET /alerts` (Fallback Polling) | `GET /api/v1/alerts` | None | `List[Alert]` (each item matches Pydantic `Alert` schema) | **MATCH** | Switched alerts listing query to join transactions to align formats with the SSE stream. |

---

### Core Resolutions Summary
1. **Model Value Standardizations**: Standardized the risk evaluation fields from hardcoded paths. The UI now tracks `final_verdict`, `final_risk_score`, and `explanation_narrative`.
2. **Alert Metric Enrichment**: Resolved transactional column absence in `fraud_events` table by performing C-level `LEFT JOIN transactions` on SQLite select operations, supplying instantaneous `amount`, `risk_score`, and `channel` data.
3. **CORS wildcarding**: Opened API route CORS configurations to wildcard `"*"` so that the dashboard port is never rejected by browser security policies.
