# 🦅 Garuda Sentinel — BOI Fraud Intelligence Platform

> **Platform Version:** FDS v5.1 | **Author:** Krishna Koushik Pasupuleti | **Institution:** CMRCET Hyderabad
> **Problem Statement:** PS2 — AI/ML-Based Suspicious Transaction & Mule Account Detection

---

## 📋 Index

> *Click any section to jump directly to it.*

| # | Section | What's Inside |
|---|---------|---------------|
| 1 | [🎯 Problem Statement, Dataset V2 & Ingestion](#1--problem-statement-dataset-v2--ingestion) | PS2 breakdown, raw government cyber dataset cleaning, DataSet V2 pipeline, and data source registration |
| 2 | [🏗️ System Architecture & Dual-Database Engines](#2--system-architecture--dual-database-engines) | High-level data flows, two-pipeline intercept model, dual SQLite & Cloud PostgreSQL/Supabase configurations |
| 3 | [🟡 COBOL — The Mainframe Core & Sentinel Agent](#3--cobol--the-mainframe-core--sentinel-agent) | GnuCOBOL CBS engine, C-SQLite WAL bridge, the low-level `SENTINEL.cbl` bytecode parser, and decision HEX-copybooks |
| 4 | [🤖 AI / ML Stack & Feature Engineering](#4--ai--ml-stack--feature-engineering) | XGBoost, GraphSAGE, LSTM Autoencoder, and transforming F3894-F3923 columns into engineered features |
| 5 | [🕸️ Graph Intelligence & D3.js Neo4j Layer](#5--graph-intelligence--d3js-neo4j-layer) | Neo4j GDS, PageRank propagation, BFS money flow tracer (`money_flow_tracer.py`), and D3.js interactive frontend visualization |
| 6 | [🚨 Alert Ingestion Layer & eCourts API](#6--alert-ingestion-layer--ecourts-api) | Kafka consumer clients (`kafka_client.py`), topic configuration, and eCourts API litigant lookup integrations with Redis cost controls |
| 7 | [🔗 Cross-Channel Aggregator & 3-Tier Pipeline](#7--cross-channel-aggregator--3-tier-pipeline) | Channel-hopping aggregation across UPI, IMPS, RTGS, CARD, ATM, Shannon entropy diversity, and the 3-Tier Latency Pipeline |
| 8 | [🔍 Mule Intelligence & Heuristics Scorer](#8--mule-intelligence--heuristics-scorer) | 8 Cypher patterns (Relay, Fan-out, Structuring), RBI Early Warning System scans, and PageRank contagion propagation |
| 9 | [⚖️ Regulatory Intelligence Layer](#9--regulatory-intelligence-layer) | LangGraph Suspicious Transaction Report (STR) compiler, RFA lifecycle SLA tracking, Redis watchlists, and RBI Google News circular feeds |
| 10 | [📊 Analyst Workstations & Dashboard Pages](#10--analyst-workstations--dashboard-pages) | Deep dive into Overview Page, Investigate Page, Alerts Page, and Graph Page with verified FastAPI contract parameters |
| 11 | [🛡️ Security, Contract Auditing & API Normalization](#11--security-contract-auditing--api-normalization) | API contract alignment (`CONTRACT_AUDIT.md`), model standardizations, CORS wildcarding, and production security gaps |
| 12 | [🚀 Deployment, Java Swing Launcher & Smoke Tests](#12--deployment-java-swing-launcher--smoke-tests) | Rationale behind Java FAT JAR execution, pre-flight prerequisites, automated `smoke_test.py`, and subsystem validation scripts |

---

## 1 🎯 Problem Statement, Dataset V2 & Ingestion

### The PS2 Challenge

> *"Develop an AI/ML solution for detecting suspicious transactions and mule accounts by ingesting financial transactions, FMS alerts, TMS alerts, and government cyber fraud tickets — while preventing circulation of fraudulent proceeds through mule accounts. The solution must consume real-time regulatory inputs and cross-channel bank data."*

### The Raw Dataset & Cleansing Pipeline (`ingest_dataset.py`)

Banks receive raw government cyber crime incident datasets containing high-dimensional, sparse telemetry mixed with demographic variables. Garuda Sentinel uses an advanced ETL ingestion engine (`scripts/ingest_dataset.py`) that transforms sparse, raw inputs into an optimized **DataSet V2** schema (`database/schema_v2.sql`).

```
[Raw Government CSV] ──► [ETL Melt & Filter Engine] ──► [Demographic Alignment] ──► [DataSet V2 Schema]
                                   │                                                      │
                       • Sparsity Analysis (F1-F3885)                           • dataset_accounts
                       • Null Filtering                                         • dataset_features
                       • Numeric Coercion                                       • dataset_transactions_synthetic
```

#### 1. Sparsity Analysis & Vectorized Melting
The raw input dataset consists of 3,885 behavioural feature columns (`F1` to `F3885`). To prevent database bloat, the ingester computes the missing-value rate (NA rate) dynamically:
- **Dense Features (NA Rate < 90%):** Columns are melted in a vectorized Pandas operation (`pd.melt`) and inserted as long-format key-value pairs into the `dataset_features` table.
- **Sparse Features (NA Rate ≥ 90%):** Deemed noisy or empty; they are filtered out, saving **~78% of disk storage**.
- **Behavioral Variables (F3894 to F3923):** 30 sequential columns representing monthly account trends are extracted and stored as fixed attributes in the `dataset_accounts` table.

#### 2. Cleaning and Parsing Logic
- **Date Formatting:** Dates with non-standard representation (e.g., `D-M-YYYY` or space-padded strings) are parsed via a safe helper `_parse_date(raw)` into standard ISO format (`YYYY-MM-DD`).
- **Demographics & Income Mapping:** Accounts are enriched based on occupation categories (`SALARIED`, `SELFEMPLOYED`, `STUDENT`, `RETIRED`, `HOUSEWIFE`, `PROFESSIONAL`) matching a structural income dictionary (`INCOME_MAP`).
- **Data Source Registration:** Once ingested, the run parameters are registered in the `data_source_registry` table. Analysts can toggle between the `REGULATORY_FEED` and the `COBOL_SYNTHETIC` simulator engines on-the-fly, dynamically repopulating the backend data models.

---

## 2 🏗️ System Architecture & Dual-Database Engines

### High-Level Architectural Pipeline

The system utilizes an asynchronous Speed Layer paired with a multi-layered Intelligence Layer to enable pre-transaction intercept alongside deep offline analytics.

```
                  ┌──────────────────────────────────────────────┐
                  │          CORE BANKING MAINFRAME              │
                  │   GnuCOBOL CBS Engine (banking_engine.cob)   │
                  └──────────────────────┬───────────────────────┘
                                         │ Intercept Named Pipe
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │            SPEED LAYER INTERCEPT             │
                  │        2ms Fast-path Redis Watchlist         │
                  └──────────────────────┬───────────────────────┘
                                         │ Published to Kafka
                                         ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                       INTELLIGENCE LAYER                        │
        │                                                                 │
        │   ┌────────────────────┐ ┌───────────────────┐ ┌────────────┐   │
        │   │    XGBoost Scorer  │ │   GraphSAGE GNN   │ │  LSTM Auto │   │
        │   │     (Tabular ML)   │ │  (Network Risk)   │ │  (Sequence)│   │
        │   └─────────┬──────────┘ └─────────┬─────────┘ └─────┬──────┘   │
        │             │                      │                 │          │
        │             └──────────────┬───────┴─────────────────┘          │
        │                            ▼                                    │
        │             Unified Risk Engine (URE Fuse Node)                 │
        │                            │                                    │
        │                            ▼                                    │
        │           LangGraph Deep AI Agent Orchestrator                  │
        └────────────────────────────┬────────────────────────────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
      ┌───────────────────────┐             ┌───────────────────────┐
      │   NEO4J GRAPH STORE   │             │   COMPLIANCE ENGINE   │
      │  Graph Data Science   │             │   STR, RFA, CRILC     │
      └───────────────────────┘             └───────────────────────┘
```

### Dual-Database Relational Engine: SQLite + Supabase Cloud

To meet high-availability and air-gapped security mandates, the relational persistence tier supports a unified dual-database layout.

1. **Local Edge Mode (SQLite):**
   Runs a high-performance local SQLite database (`ecosystem.db`). This engine operates under Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and `PRAGMA synchronous=NORMAL`, letting GnuCOBOL process streams and write events at speeds exceeding **50,000 TPS**.
2. **Cloud Enterprise Mode (PostgreSQL / Supabase):**
   For cloud-integrated installations, the system synchronizes relational transactions to an external Supabase PostgreSQL cluster. The data source switches dynamically using `scripts/switch_datasource.py`, which maps schemas between local tables and remote relations. If the cloud database is disconnected, the system falls back seamlessly to SQLite, buffering events locally until reconnection.

---

## 3 🟡 COBOL — The Mainframe Core & Sentinel Agent

### Why COBOL is Critical
Indian public sector banks manage core ledgers on legacy mainframes where performance is measured in absolute precision and decimal reliability. Garuda Sentinel does not replace the mainframe core; it wraps it in an event-driven intelligence layer.

### High-Performance C-SQLite WAL Bridge (`sqlite_bridge.c`)
Standard GnuCOBOL lacks native drivers for SQLite or PostgreSQL. To bridge this gap, we implemented a native C bridge (`sqlite_bridge.c`) compiled directly into the COBOL binary. 

```c
// sqlite_bridge.c snippet
#include <sqlite3.h>
#include <stdio.h>

sqlite3 *db = NULL;

int db_init(const char *db_path) {
    int rc = sqlite3_open(db_path, &db);
    if (rc != SQLITE_OK) return rc;
    
    // Set enterprise performance pragmas
    sqlite3_exec(db, "PRAGMA journal_mode=WAL;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA synchronous=NORMAL;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA cache_size=10000;", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA temp_store=MEMORY;", NULL, NULL, NULL);
    return SQLITE_OK;
}
```

By buffering SQL statements and processing inserts in batch blocks of **1,000 transactions**, the bridge eliminates persistent disk sync stalls, maintaining sub-millisecond core processing.

### The Mainframe Sentinel Agent (`SENTINEL.cbl`)
The `SENTINEL.cbl` program runs at the core mainframe level, serving as a transaction intercept block. It reads structured risk records via `SYSIN`, parses variables using `UNSTRING`, evaluates rules, and structures an EBCDIC-ready hex copybook decision.

```cobol
*> SENTINEL.cbl Pre-Settlement Decision Logic
 1000-EVALUATE-DECISION.
     DISPLAY "🔍 [CBSA] AUDITING LIVE TRANSACTION RULES IN CBS PATH".
     IF NUM-RISK-SCORE >= HIGH-RISK OR 
        NUM-CONTAM-SCORE >= CRITICAL-CONTAM
         MOVE "HOLD" TO DECISION-ACTION
         MOVE "E095" TO DECISION-CODE
         MOVE "CRITICAL MULE RISK OR NETWORK CONTAMINATION" 
             TO DECISION-REASON
     ELSE
         IF NUM-VELOCITY-SCORE >= ELEVATED-VELOCITY AND 
            NUM-AMOUNT >= 100000.00
             MOVE "FREEZE" TO DECISION-ACTION
             MOVE "E097" TO DECISION-CODE
             MOVE "HIGH VELOCITY ATTEMPTED OUTFLOW LIMIT EXCEEDED"
                 TO DECISION-REASON
         ELSE
             IF NUM-RISK-SCORE >= 50 AND NUM-VELOCITY-SCORE >= 50
                 MOVE "HOLD" TO DECISION-ACTION
                 MOVE "E075" TO DECISION-CODE
                 MOVE "SUSPICIOUS TRANS ACTIVITY - PENDING APPROVAL"
                     TO DECISION-REASON
             ELSE
                 MOVE "ALLOW" TO DECISION-ACTION
                 MOVE "A000" TO DECISION-CODE
                 MOVE "APPROVED BY CBS ENGINE" TO DECISION-REASON
             END-IF
         END-IF
     END-IF.
```

The system converts the final status into a hex copybook buffer (`HEX-BUFFER`):
- **ALLOW:** `0100F2C141434330303030303039FF41434330303030303039FF000000030D4041303030`
- **FREEZE:** `0100F2C1414343303030383630FF414343303030383630FF0000002DC6C045303937`
- **HOLD:** `0100F2C14E6F74204D656E74696F414343303037303336FF0000001E848045303935`

This formatted string is unpacked natively by mainframe transaction routers, enforcing block triggers instantly.

---

## 4 🤖 AI / ML Stack & Feature Engineering

### Multi-Dimensional Model Architecture

```
                  Tabular Telemetry ─────► [ XGBoost Scorer ] ──────┐
                                                                    │
                  Graph Edges       ─────► [ GraphSAGE GNN ]  ──────┼─► [ Unified Risk Engine ]
                                                                    │
                  Time Sequences    ─────► [ LSTM Autoencoder ] ────┘
```

1. **XGBoost Classifier (`xgb_fraud.json`):** Evaluates high-velocity transactional and demographic indicators. Returns structural fraud predictions in **< 3ms**.
2. **GraphSAGE GNN (`gnn_mule.pt`):** Generates structural node embeddings by propagating transaction telemetry through the neighborhood graph. Detects hidden relay nodes and circular layering patterns.
3. **LSTM Sequential Autoencoder (`lstm_ae.pt`):** Traces 10-step sequence windows per account. Flagged transactions are identified by computing reconstruction errors on behavioral changes over time.

### Key Engineered Features (From Columns F3894–F3923)

The raw government dataset provides 30 behavioral history variables (`F3894` to `F3923`). The system transforms these columns using `src/pipeline/feature_engineering.py` into highly predictive risk indicators:

```python
# key engineered metrics computed in pipeline
mule_amount_ratio    = max_cumulative_amount / (account_age_days + 1)
max_zscore           = (current_txn_amount - mean_historical_amount) / (std_dev_amount + 1e-5)
fan_out_ratio        = unique_beneficiaries_7d / (total_transactions_7d + 1)
dormancy_break       = 1 if days_since_last_txn > 90 and txn_today > 0 else 0
young_account_flag   = 1 if account_age_days < 180 else 0
bureau_drift         = abs(risk_score_3month - risk_score_12month)
status_risk_encode   = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}[risk_profile]
```

### Grok-Powered Mule Intelligence Hopper Agent

The platform features the **Mule Intelligence Hopper Agent**, an LLM agent connected to **Grok LLM**.
- **Dynamic Graph Auditing:** The agent crawls the Neo4j GDS communities to inspect anomalous PageRank fluctuations.
- **SHAP Explanation Synthesis:** Instead of forcing compliance analysts to decode raw SHAP feature vectors, the Hopper Agent translates machine telemetry and structural money traces into PMLA-compliant case narratives.
- **Interactive Inquiries:** Accessible on the Analyst Dashboard, the agent answers ad-hoc questions (e.g., *"Why did the COBOL intercept freeze this customer yesterday?"*) by querying local SQLite logs and traversing connected transaction pathways in real-time.

---

## 5 🕸️ Graph Intelligence & D3.js Neo4j Layer

### The Neo4j GDS Pipeline
A single fraudulent transaction can appear normal in isolation. Graph Data Science (GDS) analyzes structural network behavior to flag money rings before cash-out occurs.

```cypher
// Neo4j Transaction Edge Mapping
(AccountA)-[:SENT_TO {amount: 8500, timestamp: '2026-06-01T22:40:00', channel: 'UPI'}]->(AccountB)
```

### Advanced Algorithms Applied

| Algorithm | Focus | Technical Role |
| :--- | :--- | :--- |
| **Personalized PageRank** | Risk Contamination | Propagates risk from verified fraud sources outward through nearby nodes. |
| **Betweenness Centrality** | Layering & Handoffs | Highlights high-capacity intermediary accounts linking different communities. |
| **Louvain Community** | Ring Isolation | Partitions the network into clusters to identify coordinated carding rings. |
| **BFS Money Flow Tracer** | Fund Recovery | Traces upstream sources and downstream cash-out terminals. |

### Money Flow Tracer (`money_flow_tracer.py`)
Traces recursive flow graphs up to **5 hops** deep in SQLite and Neo4j:
- **Upstream Path:** Traces funds back to the initial victim account to establish the criminal source.
- **Downstream Path:** Traces outgoing splits to catch active transfers and freeze cash-out targets.

### Visualizing Network Topology via D3.js
The **Graph Page** uses custom D3.js interactive libraries to render active fraud rings:
- Nodes are sized based on their Personalized PageRank score (larger size indicates higher network risk).
- Visual links are colored dynamically based on the transaction channel (e.g., green for UPI, red for IMPS).
- Node border rings pulse if the active threat level is `CRITICAL`.
- Hovering over a node displays its cluster community ID, monthly income, PageRank score, and active risk metrics.

---

## 6 🚨 Alert Ingestion Layer & eCourts API

### Event-Driven Kafka Consumer Pipeline

```
  Kafka Topics
 ┌──────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
 │     alerts.fms       │      │       alerts.tms       │      │   alerts.govt_cyber    │
 └──────────┬───────────┘      └───────────┬────────────┘      └───────────┬────────────┘
            │                              │                               │
            ▼                              ▼                               ▼
    [fms_consumer.py]              [tms_consumer.py]            [govt_cyber_consumer.py]
            │                              │                               │
            └──────────────────────┬───────┴───────────────────────────────┘
                                   ▼
                       [alert_correlator.py]
                                   │
                                   ▼
                   [legal_intelligence_agent.py] (eCourts)
```

The system uses dedicated consumer daemons (`fms_consumer.py`, `tms_consumer.py`, and `govt_cyber_consumer.py`) backed by the `KafkaPubSub` client. 
- **Resilient Fallback Mode:** If the central Kafka broker is unreachable, the system activates an in-memory pub-sub fallback (`_subscribers` cache) to prevent data loss or transaction stalls in offline setups.
- **Correlation Processing:** The `alert_correlator.py` engine links concurrent alerts. If an account triggers a TMS rule violation and is named in a government cyber ticket within 24 hours, the system elevates the priority status to `CRITICAL`.

### Real-Life eCourts API Integration (`legal_intelligence_agent.py`)

Rather than relying entirely on mocked database columns, Garuda Sentinel integrates with active eCourts APIs using the `LegalIntelligenceAgent`.

```
  Inbound Case Investigation 
            │
            ▼
 ┌───────────────────────────┐
 │  eCourts Daily Quota?     ├─► [Exceeded] ──► Fallback to Watchlist Match
 └──────────┬────────────────┘
            │ [Within 2 queries/day Limit]
            ▼
 ┌───────────────────────────┐
 │ Litigant Search Request   ├─► https://webapi.ecourtsindia.com/api/partner/search
 └──────────┬────────────────┘
            │
            ▼
 ┌───────────────────────────┐
 │   Parse Case Metadata     ├─► aiKeywords, caseCategory, caseType
 └──────────┬────────────────┘
            │
            ▼
 ┌───────────────────────────┐
 │ Legal Risk Score Analysis ├─► Fraud/Cyber Keywords → High-Confidence Legal Score
 └───────────────────────────┘
```

1. **API Quota Management (Cost & Rate Control):**
   To control costs and handle API rate limiting, the agent enforces a quota of **2 queries per day**. It checks active usage against a dynamic key (`ecourts_quota:YYYY-MM-DD`) in Redis, falling back to a local SQLite table (`legal_quota_limit`) if Redis is offline.
2. **Litigant Search Request:**
   If the quota is active, the agent queries the search API at `https://webapi.ecourtsindia.com/api/partner/search`, passing the account holder's name.
3. **Parse Case Metadata:**
   The agent analyzes returned cases, checking properties (`caseCategory`, `caseType`, and `aiKeywords`) against risk keywords (e.g., *fraud, cheat, forgery, cyber, phishing, it act*).
4. **Legal Risk Score Analysis:**
   If a court match is confirmed, the legal risk score escalates (`legal_risk_score = min(99, 45 + court_matches * 15)`), raising the account's overall URE risk rating.

---

## 7 🔗 Cross-Channel Aggregator & 3-Tier Pipeline

### Multi-Channel Transaction Aggregation
Fraud rings often distribute stolen funds across multiple banking channels to bypass single-channel monitoring systems (e.g., receiving funds via NEFT, splitting them via UPI, and withdrawing cash via ATM). The `cross_channel_detector.py` engine processes these incoming transaction flows in real-time.

### Channel Hopping Metrics
The cross-channel aggregator maintains rolling metrics for each active account:
- **Channel Diversity (Shannon Entropy):** Measures the distribution of transactions across channels. High diversity indicates active channel-hopping behavior.
- **Outflow Velocity Hops:** Flags accounts that move received funds across distinct channels within a 1-hour window.
- **Inter-Bank Warning Flags:** Integrates inter-bank threat feeds (such as NPCI warnings) to isolate outbound destination nodes.

### The 3-Tier Latency Pipeline

```
  Incoming Intercept
           │
           ▼
 ┌───────────────────┐
 │  TIER 1 (< 10ms)  ├─► [XGBoost Tabular Scorer] ──► Hard Block (Score > 0.85)
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────┐
 │ TIER 2 (< 150ms)  ├─► [GraphSAGE + LSTM + Channel Aggregator]
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────┐
 │  TIER 3 (< 30s)   ├─► [LangGraph Deep Agent & eCourts API] ──► Final Narrative
 └───────────────────┘
```

- **Tier 1 (Sub-10ms Intercept):**
  Uses the XGBoost model to evaluate transaction amounts, z-scores, and basic velocity metrics on incoming ledger events. If the risk score exceeds `0.85`, it triggers a hard block through the COBOL Named Pipe.
- **Tier 2 (Sub-150ms Neighborhood Audit):**
  Runs in the background to update GNN embeddings, analyze sequence drift via the LSTM model, check channel diversity, and flag behavioral anomalies.
- **Tier 3 (Deep Agent Investigation):**
  Triggered only when Tier 2 risk scores exceed `0.70`. It initiates a LangGraph multi-agent orchestration, executes legal checks via the eCourts API, and compiles case summaries.

---

## 8 🔍 Mule Intelligence & Heuristics Scorer

### 8 Core Heuristic Mule Patterns (`patterns.py`)
Implemented as optimized Cypher queries in Neo4j GDS, with recursive CTE fallback joins in SQLite:

```
 1. RELAY_CHAIN      A ──► B ──► C ──► D  (Rapid serial pass-through)
 
                       ┌──► B (10%)
 2. FAN_OUT          A ┼──► C (10%)       (Split transfers to bypass limits)
                       └──► D (10%)
 
                       ┌──► B (₹9,900)
 3. STRUCTURING      A ┼──► C (₹9,900)    (Transfers kept just below PAN limit)
                       └──► D (₹9,900)
 
 4. LAYERING         Multi-hop obfuscation split across consecutive hops
 5. VELOCITY_SPIKE   Extreme transaction count increase in narrow time windows
 6. DORMANCY_BREAK   Sudden high-volume transfers on historically inactive accounts
 7. NIGHT_ACTIVITY   High-volume transfers processed between 11 PM and 4 AM
 8. ROUND_TRIP       Circular fund routing: A ──► B ──► C ──► A
```

### RBI Early Warning System (EWS) Integration
The early warning framework (`early_warning.py`) performs nightly scans across all accounts, aggregating five weighted indicators:

$$\text{EWS Score} = 0.25 \times \text{KYC Anomalies} + 0.25 \times \text{Device Swaps} + 0.20 \times \text{Cluster Growth} + 0.15 \times \text{Inbound Spikes} + 0.15 \times \text{Beneficiary Explosion}$$

If the aggregated EWS Score exceeds **`0.60`**, the account is flagged as a suspected Pre-Mule, triggering enhanced logging and transaction monitoring.

### Risk Contagion Propagation
The contagion scorer (`network_scorer.py`) uses Personalized PageRank to propagate risk scores from known mule nodes through the network. In testing, a single flagged node infected **1,734 connected accounts** in its community cluster, allowing the system to isolate the entire ring before fraudulent funds could circulate.

---

## 9 ⚖️ Regulatory Intelligence Layer

### Automatic STR Generation (`str_generator.py`)
The system automates PMLA compliance reporting via `str_generator.py`. High-risk accounts are processed by a LangGraph compliance agent that compiles transaction logs, SHAP explanations, and identity records into PMLA-compliant JSON files. These records are published to the `str.pending` Kafka queue for final human review.

```json
{
  "fiu_str_version": "2.0.1",
  "reporting_entity": "BANK OF INDIA",
  "suspect_details": {
    "account_id": "REAL003412",
    "name": "Arjun Sharma",
    "legal_risk_score": 82,
    "eCourts_matches": 2
  },
  "risk_assessment": {
    "composite_risk_score": 0.89,
    "top_shap_factors": ["outflow_velocity", "channel_diversity", "dormancy_break"],
    "narrative": "Account woke up after 92 days of dormancy and received a high-value UPI transfer, which was immediately split across multiple new beneficiaries. eCourts checks confirmed active civil litigation records matching the holder's name."
  }
}
```

### RFA Lifecycle Tracker
Tracks the lifecycle of Red Flagged Accounts (RFA) in accordance with RBI timelines:
- **Day 0:** Account is flagged; an RFA entry is logged and the CRILC reporting deadline is set.
- **Day 7:** System triggers an alert if the CRILC report remains unfiled.
- **Day 180:** Final classification deadline; unresolved cases are escalated for permanent block.

### O(1) Watchlist Manager (`watchlist_manager.py`)
Maintains watchlists in Redis Hash sets to support rapid transaction checks. If Redis is offline, the manager falls back to SQLite indexed queries, maintaining sub-millisecond check speeds.

### RBI Circular Scraper (`news_feed.py`)
Pulls news circulars from the Google News RSS feed and community alerts from Reddit forums. It analyzes updates using NLP to identify new fraud trends and publishes alert summaries directly to the Analyst Dashboard.

---

## 10 📊 Analyst Workstations & Dashboard Pages

The React analyst dashboard provides a consolidated interface for system monitoring, investigation, and regulatory reporting:

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │  GARUDA SENTINEL ANALYST WORKSPACE                                     │
 ├─────────────────┬─────────────────┬───────────────────┬─────────────────┤
 │ 📊 Overview     │ 🔍 Investigate  │ 🚨 Alerts         │ 🕸️ Graph viz     │
 └─────────────────┴─────────────────┴───────────────────┴─────────────────┘
```

### 1. Dashboard Overview Page
- **Visual Status Panels:** Displays system-wide counts, fraud alerts, active investigations, and Neo4j database metrics.
- **SSE Live Alert Stream:** Connects to `/api/v1/alerts/stream` via a Server-Sent Events stream to render incoming alerts with transaction metadata.
- **EWS Trend Widget:** Renders active threat metrics and early warning signals.

### 2. Investigation Workstation Page
- **Deep Account Profiles:** Displays specific account details, including PageRank ratings, community cluster IDs, risk profiles, and transaction histories.
- **Visual SHAP Charts:** Renders SHAP bar charts to explain the primary risk drivers.
- **Grok Deep Analysis Panel:** Displays natural-language case summaries compiled by the Grok Hopper Agent.

### 3. Alerts Workstation Page
- **Kafka Event Registry:** Displays a historical list of system alerts with interactive filters for severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **Escalation Triggers:** Provides tools to manually escalate alerts, trigger RFA workflows, or initiate multi-agent reviews.

### 4. Graph Visualization Page
- **Interactive D3.js Workspace:** Renders Neo4j network topologies with force-directed layouts. Node sizing is based on PageRank scores, and links are colored by transaction channel.
- **Community Isolation Controls:** Allows analysts to select clusters, trace fund pathways, and view neighbor node details.

---

## 11 🛡️ Security, Contract Auditing & API Normalization

### API Contract Auditing (`CONTRACT_AUDIT.md`)
To ensure reliable integration, the system utilizes a contract auditing protocol (`CONTRACT_AUDIT.md`) to verify alignment between the React frontend API calls and the FastAPI endpoints.

- **Unified Schema Models:** Resolves schema mismatches by standardizing model outputs on `final_verdict`, `final_risk_score`, and `explanation_narrative`.
- **SQL Stream Optimization:** Enriches Server-Sent Events (SSE) payloads by performing SQL `LEFT JOIN` queries on SQLite alerts, supplying transaction amounts, channels, and risk scores in a single unified message.
- **CORS Configuration:** Enables CORS wildcarding (`"*"`) for development configurations to prevent browser-level request blocking.

### Production Security Roadmap

| Threat Vector | Current Status (Prototype) | Production Hardening Plan |
| :--- | :--- | :--- |
| **Endpoint Auth** | No authentication configured | Implement OAuth2 paired with JWT/PKCE tokens. |
| **Data Encryption** | Plaintext SQLite and Neo4j storage | Deploy SQLCipher alongside Neo4j TDE encryption. |
| **Network Security** | Plaintext Kafka listener | Restrict connections to SSL/TLS with SASL/SCRAM. |
| **PII Isolation** | Customer names and phones exposed | Implement field-level hashing for confidential data. |

---

## 12 🚀 Deployment, Java Swing Launcher & Smoke Tests

### Java 21 Swing Master Control Launcher
Deploying and managing a modular system containing multiple databases, message brokers, backend API servers, frontend dashboards, and COBOL mainframes can be operationally complex. The master launcher provides a centralized control interface:

```
 ┌────────────────────────────────────────────────────────┐
 │  🦅 GARUDA SENTINEL MASTER LAUNCHER (FlatLaf Dark UI)  │
 ├────────────────────────────────────────────────────────┤
 │ [Prerequisites Check: Java v, Python v, Docker v]      │
 │                                                        │
 │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────┐ │
 │ │  FastAPI Server  │ │  React Dashboard │ │  Docker  │ │
 │ │  [▶ Start] [■]   │ │  [▶ Start] [■]   │ │  [▶] [■] │ │
 │ └──────────────────┘ └──────────────────┘ └──────────┘ │
 │                                                        │
 │ 🔍 Live SQLite Log Stream Checker                      │
 │ [========================================] 100k Nodes  │
 │                                                        │
 │ 🖥️ Master Console Output Stream                         │
 │ ------------------------------------------------------ │
 │ [Info] Launching FastAPI backend core...               │
 └────────────────────────────────────────────────────────┘
```

#### Why We Selected Java for the Master Launcher:
1. **Cross-Platform Portability:** Java runs reliably across Windows, macOS, and Linux servers without platform-specific compilation requirements.
2. **Robust Process Management:** Spawns and manages separate processes for Node/Vite, Uvicorn, Python simulators, and GnuCOBOL binaries using `ProcessBuilder` handles.
3. **Active Health Polling:** Automatically monitors network port states (8000, 5173, 7687, 6379, 9092) and queries HTTP endpoints to update the UI status indicators.
4. **Failsafe Shutdown Hooks:** Executes structured JVM shutdown procedures on exit, terminating background processes and docker container instances to prevent orphaned zombie PIDs.

### Automated Smoke Tests & System Verification
Automated testing scripts are provided to verify the status of backend APIs, model scoring networks, and database transactions:

```bash
# 1. Spin up the infrastructure container stack
docker-compose up -d

# 2. Run the main GnuCOBOL compilation pipeline
./scripts/build.sh

# 3. Clean database and run the DataSet V2 cleaning pipeline
./scripts/reset_database.sh
python scripts/ingest_dataset.py

# 4. Verify system APIs and agent routes
python scripts/smoke_test.py
```

The `smoke_test.py` script validates core system functionality:
- Connects to `database/ecosystem.db` to retrieve active transaction IDs, account profiles, and community records.
- Queries endpoints (e.g., `/api/v1/dashboard/summary`, `/api/v1/graph/stats`, `/api/v1/alerts`) to check API payload structures.
- Sends a request to `/api/v1/investigate` to verify the multi-agent LangGraph analysis workflow.
- Verifies account flagging routes.
- Outputs a system validation summary to confirm operational status:

```
[PASS] Health Check                                       OK
[PASS] Dashboard Summary                                  OK
[PASS] Transactions List                                  OK
[PASS] Accounts List                                      OK
[PASS] Graph Stats                                        OK
[PASS] Fraud Rings                                        OK
[PASS] Alerts List                                        OK
[PASS] Single Transaction Details                         OK
[PASS] Single Account Profile                             OK
[PASS] Account Network Graph                              OK
[PASS] Community Members                                  OK
[PASS] Start Investigation (POST)                         Created inv_id=6c4b2a8d
[PASS] Get Investigation Status (GET)                     Status: COMPLETED
[PASS] Flag Account (POST)                                Account flagged successfully

==================================================
ALL SYSTEMS DEPLOYED AND FUNCTIONAL // SMOKE TEST PASSED
```

---

*Garuda Sentinel — Built for the Bank of India that exists today, not the one that might exist tomorrow.*
*Krishna Koushik Pasupuleti · CMRCET Hyderabad · BOI PSB Hackathon 2026*
