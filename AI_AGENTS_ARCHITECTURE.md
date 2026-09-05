# Garuda Sentinel — AI Agents Architecture

> Full architecture reference for the AI agents inside the Bank of India (BOI) Garuda Sentinel
> fraud-intelligence platform. This document maps how the **Fraud Investigation Agent**,
> the **Mule Intelligence subsystem**, the **COBOL Sentinel Agent**, and the supporting
> **LangGraph multi-agent orchestrator** are accessed, how their workflows run, how they use
> the **Groq LLM API**, what language each tier is written in, and how multi-step agentic
> processes are coordinated.

All diagrams below are [Mermaid](https://mermaid.js.org/) — they render natively on GitHub,
in VS Code (Markdown Preview Mermaid Support), and on most Markdown viewers.

---

## 1. System Context — Agents at a Glance

```mermaid
graph TB
    subgraph Client["Frontend — React + TypeScript (Vite)"]
        UI["Investigator Workstation UI<br/>OverviewPage / RegulatoryPage<br/>GovDataIntelligence"]
    end

    subgraph API["API Tier — FastAPI (Python 3.12)"]
        R1["/agent-investigation<br/>fraud_agent.py"]
        R2["/cobol-sentinel<br/>cobol_sentinel.py"]
        R3["/investigate<br/>investigations.py"]
        R4["/mule/*<br/>mule_intelligence.py"]
    end

    subgraph Agents["Agent Tier (Python)"]
        FIA["Fraud Investigation Agent<br/>(Groq LLM, single-shot)"]
        ORCH["LangGraph Orchestrator<br/>(5-node state machine)"]
        MULE["Mule Intelligence<br/>(deterministic analytics)"]
        LEGAL["Legal Intelligence Agent<br/>(eCourts API)"]
    end

    subgraph Runtime["COBOL Sentinel Runtime (GnuCOBOL)"]
        BRIDGE["Kafka COBOL Bridge<br/>sentinel_bridge.py"]
        COBOL["SENTINEL.cbl<br/>GnuCOBOL binary"]
    end

    subgraph Ext["External / Data Services"]
        GROQ["Groq Cloud API<br/>llama-3.3-70b-versatile"]
        ECOURTS["eCourts India WebAPI"]
        KAFKA["Apache Kafka"]
        NEO["Neo4j Graph DB"]
        REDIS["Redis"]
        SQLITE["SQLite Core Ledger"]
    end

    UI --> R1 & R2 & R3 & R4
    R1 --> FIA --> GROQ
    R2 --> COBOL_PATH["Groq entity extraction"] --> GROQ
    R2 --> LEGAL --> ECOURTS
    R2 --> KAFKA --> BRIDGE --> COBOL
    R3 --> ORCH
    R4 --> MULE
    ORCH --> NEO & REDIS
    MULE --> SQLITE
    FIA --> SQLITE
    R2 --> SQLITE

    style FIA fill:#f9d5e5
    style ORCH fill:#d5e8f9
    style MULE fill:#d5f9e8
    style COBOL fill:#f9f0d5
```

### Agent inventory & implementation language

| Agent / Subsystem | Language | LLM? | Access Path | Style |
|---|---|---|---|---|
| **Fraud Investigation Agent** | Python (FastAPI router) | ✅ Groq `llama-3.3-70b-versatile` | `POST /api/v1/agent-investigation/investigate` | Single-shot LLM report generation |
| **COBOL Sentinel Agent** | **COBOL** (GnuCOBOL) + Python bridge | ✅ Groq (entity extraction only) | `POST /api/v1/cobol-sentinel/intercept` | LLM extract → deterministic scoring → COBOL decision |
| **LangGraph Orchestrator** | Python (LangGraph) | ❌ (rule + ML based) | `POST /api/v1/investigate` | 5-node stateful multi-agent graph |
| **Mule Intelligence** | Python (SQLite analytics) | ❌ | `GET /api/v1/mule/*` | Deterministic graph/flow analytics |
| **Legal Intelligence Agent** | Python | ❌ (REST enrichment) | Invoked inside COBOL Sentinel | Quota-gated external API enrichment |

---

## 2. The Three Agentic Models Used

The platform deliberately uses **three different agentic patterns** depending on the trust and
determinism requirements of the task:

```mermaid
graph LR
    subgraph P1["Pattern A — LLM Generative Agent"]
        A1["Fraud Investigation Agent<br/>Groq LLM produces narrative<br/>+ 4-page PDF report"]
    end
    subgraph P2["Pattern B — Stateful Multi-Agent Graph"]
        A2["LangGraph Orchestrator<br/>Graph→Temporal→Behavioral<br/>→Fusion→(Regulatory)→Explain"]
    end
    subgraph P3["Pattern C — Hybrid LLM + Deterministic Mainframe"]
        A3["COBOL Sentinel<br/>LLM extracts entities →<br/>Python scores → COBOL decides"]
    end

    P1 -. "creativity, reporting" .-> Use1["Human-readable intelligence"]
    P2 -. "explainable scoring" .-> Use2["Auditable risk verdict"]
    P3 -. "regulatory determinism" .-> Use3["Pre-settlement HOLD/ALLOW"]
```

**Why three?** LLMs are non-deterministic — acceptable for *report writing* (Pattern A) and
*entity extraction* (Pattern C input), but **never** for the actual money-movement decision.
The final HOLD/FREEZE/ALLOW verdict is computed by deterministic Python scoring and a
**COBOL mainframe rules engine** (Pattern C), so the same ticket always yields the same
banking action — a regulatory requirement.

---

## 3. Fraud Investigation Agent (Groq LLM)

**File:** `src/api/routers/fraud_agent.py` · **Endpoint:** `POST /api/v1/agent-investigation/investigate`

This is the classic generative agent: it receives ML telemetry (GNN, LSTM, XGBoost SHAP,
graph neighbors) and uses the Groq LLM to author a professional executive report plus a
structured 4-page PDF.

### 3.1 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant UI as React UI
    participant API as fraud_agent.py
    participant RL as SQLite Rate Limiter
    participant GROQ as Groq API<br/>(llama-3.3-70b-versatile)
    participant PDF as pdf_generator.py
    participant DB as SQLite

    UI->>API: POST /investigate {risk_score, community,<br/>graph_neighbors, gnn_score, lstm_score,<br/>xgboost_features, recent_transactions}
    API->>RL: check_and_increment_rate_limit()
    alt Daily cap (10/day) exceeded
        RL-->>API: raise 429
        API-->>UI: 429 Too Many Requests
    end
    RL-->>API: remaining_runs

    API->>API: Build prompt (telemetry → 4-page outline)
    API->>GROQ: POST /chat/completions<br/>temperature=0.2<br/>response_format=json_object
    GROQ-->>API: {summary_report, pdf_markdown}
    API->>API: json.loads (with markdown-fence fallback)
    API->>PDF: generate_investigation_pdf(pdf_markdown)
    PDF-->>API: report_<ts>_<community>.pdf
    API->>DB: INSERT INTO agent_reports
    API-->>UI: {report, pdf_download_url, rate_limit_remaining}

    Note over UI,DB: Later: GET /agent-investigation/download/{report_id}<br/>streams the PDF via FileResponse
```

### 3.2 Groq API usage detail

```mermaid
graph TD
    KEY["GROQ_API_KEY<br/>os.environ.get(...) with hardcoded fallback"] --> HDR
    HDR["Authorization: Bearer {key}"] --> POST
    POST["POST https://api.groq.com/openai/v1/chat/completions"] --> PAYLOAD
    PAYLOAD["model: llama-3.3-70b-versatile<br/>system: clinical compliance auditor<br/>user: telemetry + 4-page outline<br/>temperature: 0.2<br/>response_format: json_object<br/>timeout: 45s"] --> RESP
    RESP["choices[0].message.content<br/>= JSON string"] --> PARSE
    PARSE["Parse → summary_report + pdf_markdown<br/>(fallback strips ```json fences)"]
```

- **OpenAI-compatible REST** — Groq exposes the OpenAI chat-completions schema, so the code
  uses raw `requests.post`, no SDK.
- **Structured output** is forced via `response_format={"type":"json_object"}` and a strict
  two-key contract (`summary_report`, `pdf_markdown`).
- **Cost control:** absolute **10 runs/day** enforced in the `agent_rate_limit` SQLite table.

---

## 4. COBOL Sentinel Agent (Hybrid LLM → Python → Mainframe)

**Files:** `src/api/routers/cobol_sentinel.py`, `src/cobol/SENTINEL.cbl`,
`src/cobol/sentinel_bridge.py` · **Endpoint:** `POST /api/v1/cobol-sentinel/intercept`

This is the most sophisticated multi-step agent. It turns a free-text cybercrime ticket into a
pre-settlement banking decision through **8 deterministic stages**, using the LLM **only** to
parse entities out of natural language, and a real **GnuCOBOL** program for the final verdict.

### 4.1 End-to-End Multi-Step Workflow

```mermaid
flowchart TD
    START([POST /cobol-sentinel/intercept<br/>ticket_text]) --> S1

    S1["① Rate limit check<br/>cobol_rate_limit — 45/day"] --> S2
    S2["② Groq LLM entity extraction<br/>llama-3.3-70b-versatile, temp=0.0<br/>→ victim, mules[], amount, cluster"] --> S3
    S3["③ Hydrate scores from SQLite ledger<br/>accounts + mule_accounts + transactions<br/>→ known_mule_flag, cluster contamination,<br/>tx velocity/volume"] --> S4
    S4["④ Legal Intelligence Agent enrich<br/>eCourts API (quota-gated 2/day)<br/>→ court_matches, legal_risk_score"] --> S5
    S5["⑤ Deterministic multi-layer scoring<br/>mule_risk% + gov_ticket% + court_risk%<br/>→ final_composite → final_risk"] --> S6
    S6["⑥ Deterministic decision rule<br/>final_risk≥0.70 OR known_mule → HOLD/E095<br/>else ALLOW/A000"] --> S7
    S7["⑦ Build data-driven explanation<br/>(verified accounts, cluster, velocity)"] --> S8
    S8{"⑧ COBOL_SENTINEL_ENABLED?"}

    S8 -->|yes| K1["Publish risk packet to Kafka<br/>topic: sentinel-risk-events"]
    K1 --> POLL["Poll COBOL_DECISIONS_CACHE<br/>up to 2.5s, 20ms cycles"]
    POLL -->|hit| COBOLDEC["Override action/hex/explanation<br/>Decision Source = COBOL Sentinel Runtime"]
    POLL -->|timeout| PYFALL["Decision Source = Python Fallback Router"]
    S8 -->|no| PYFALL

    COBOLDEC --> SAVE
    PYFALL --> SAVE
    SAVE["⑨ INSERT INTO cobol_intercepts"] --> RESP([InterceptResponse:<br/>victim, mules, amount, cluster,<br/>risk_score, action, cobol_copybook_hex,<br/>explanation, legal_intelligence])
```

### 4.2 The Kafka ⇄ COBOL Runtime Loop

The Python router and the COBOL binary are decoupled processes connected by two Kafka topics.
A background daemon (`sentinel_bridge.py`) consumes risk events, shells out to the compiled
GnuCOBOL binary, and publishes decisions back.

```mermaid
sequenceDiagram
    autonumber
    participant API as cobol_sentinel.py (router)
    participant KP as Kafka topic<br/>sentinel-risk-events
    participant BR as sentinel_bridge.py<br/>(daemon)
    participant CB as SENTINEL (GnuCOBOL binary)
    participant KD as Kafka topic<br/>sentinel-decisions
    participant LST as Router listener thread
    participant CACHE as COBOL_DECISIONS_CACHE

    Note over LST,CACHE: At import, router spawns a daemon thread<br/>consuming sentinel-decisions into the cache

    API->>KP: producer.send(risk_payload)<br/>{account_id, cluster_id, risk_score,<br/>velocity_score, contamination_score, amount, channel}
    BR->>KP: consume risk event
    BR->>BR: format fixed-length copybook line<br/>"ACC.. CLUS.. 095 085 090 0044192.85 UPI"
    BR->>CB: subprocess.run(binary, input=line, timeout=2s)
    CB->>CB: UNSTRING packet → NUMVAL → 1000-EVALUATE-DECISION
    CB-->>BR: stdout "DECISION_RESULT: HOLD E095 <hex> <reason>"
    BR->>KD: producer.send(decision_payload)
    LST->>KD: consume decision
    LST->>CACHE: CACHE[account_id] = decision
    API->>CACHE: poll up to 2.5s for account_id
    CACHE-->>API: decision (action, code, hex, explanation)
```

### 4.3 COBOL Decision Logic (`SENTINEL.cbl`)

The mainframe program is the deterministic core. It ingests a fixed-length copybook record from
`SYSIN`, parses it with `UNSTRING`/`NUMVAL`, and applies a cascading rule ladder.

```mermaid
flowchart TD
    IN["ACCEPT INPUT-RECORD FROM SYSIN<br/>PIC X fields: account, cluster,<br/>risk%, velocity%, contam%, amount, channel"] --> PARSE
    PARSE["UNSTRING DELIMITED BY SPACES<br/>FUNCTION NUMVAL → numeric vars"] --> EVAL

    EVAL{"1000-EVALUATE-DECISION"} --> R1
    R1{"risk≥70 OR contam≥75?"} -->|yes| HOLD["HOLD / E095<br/>CRITICAL MULE RISK OR CONTAMINATION"]
    R1 -->|no| R2{"velocity≥60 AND<br/>amount≥100000?"}
    R2 -->|yes| FREEZE["FREEZE / E097<br/>HIGH VELOCITY OUTFLOW LIMIT EXCEEDED"]
    R2 -->|no| R3{"risk≥50 AND velocity≥50?"}
    R3 -->|yes| HOLD2["HOLD / E075<br/>SUSPICIOUS — PENDING APPROVAL"]
    R3 -->|no| ALLOW["ALLOW / A000<br/>APPROVED BY CBS ENGINE"]

    HOLD & FREEZE & HOLD2 & ALLOW --> HEX["2000-FORMAT-HEX-COPYBOOK<br/>build EBCDIC/hex telemetry buffer"]
    HEX --> OUT["DISPLAY DECISION_RESULT:<br/>action code hex reason"]
```

**Decision thresholds (working-storage constants):** `HIGH-RISK = 70`,
`CRITICAL-CONTAM = 75`, `ELEVATED-VELOCITY = 60`.

### 4.4 Groq usage in the COBOL Sentinel

Unlike the Fraud Investigation Agent, here Groq is used **purely as a parser** — `temperature=0.0`
for determinism — and never touches the money decision:

```mermaid
graph LR
    TICKET["Free-text cybercrime ticket"] --> GROQ
    GROQ["Groq llama-3.3-70b-versatile<br/>temp=0.0, json_object<br/>system: 'output raw JSON only'"] --> JSON
    JSON["{victim_account, suspected_mules[],<br/>amount, suspected_cluster}"] --> DETERMINISTIC
    DETERMINISTIC["Deterministic Python + COBOL<br/>(LLM output never decides HOLD/ALLOW)"]
    style GROQ fill:#f9d5e5
    style DETERMINISTIC fill:#f9f0d5
```

---

## 5. LangGraph Multi-Agent Orchestrator

**Files:** `src/agents/orchestrator.py`, `src/agents/*_agent.py`, `src/agents/state.py`
· **Endpoint:** `POST /api/v1/investigate`

This is the **stateful, multi-step agentic core** built on **LangGraph**. A shared
`FraudInvestigationState` (TypedDict) flows through five specialist agent nodes; each agent
mutates the state and passes it on. One conditional edge branches on the fused risk score.

### 5.1 Orchestration State Graph

```mermaid
stateDiagram-v2
    [*] --> graph_analysis: entry point

    graph_analysis: GraphAgent<br/>Neo4j relay/fan-out/hop-2<br/>+ GraphSAGE GNN embedding
    temporal_analysis: TemporalAgent<br/>dormancy break, velocity spike<br/>+ LSTM autoencoder anomaly
    behavioral_analysis: BehavioralAgent<br/>1h/24h velocity, amount z-score<br/>new-beneficiary heuristics
    risk_fusion: RiskFusionAgent<br/>weighted fusion 0.4/0.3/0.3<br/>→ verdict
    regulatory_agent: RegulatoryAgent<br/>SAR_REQUIRED flag
    explainability: ExplainabilityAgent<br/>narrative synthesis

    graph_analysis --> temporal_analysis
    temporal_analysis --> behavioral_analysis
    behavioral_analysis --> risk_fusion
    risk_fusion --> regulatory_agent: final_risk_score > 0.5
    risk_fusion --> explainability: final_risk_score ≤ 0.5
    regulatory_agent --> explainability
    explainability --> [*]
```

### 5.2 Shared State Object (passed between every node)

```mermaid
classDiagram
    class FraudInvestigationState {
        +str transaction_id
        +str account_id
        +Dict features
        +float graph_score
        +float temporal_score
        +float behavioral_score
        +List graph_findings
        +List temporal_findings
        +List behavioral_findings
        +Optional~List~ gnn_embedding
        +float final_risk_score
        +str final_verdict
        +str explanation_narrative
        +Optional~Dict~ shap_values
        +Dict metadata
    }

    class GraphAgent {
        +investigate(state) state
        -Neo4j driver
        -GraphSAGE GNN model
    }
    class TemporalAgent {
        +investigate(state) state
        -LSTM autoencoder
    }
    class BehavioralAgent {
        +investigate(state) state
        -Redis velocity cache
    }
    class RiskFusionAgent {
        +investigate(state) state
        -weights{graph,temporal,behavioral}
    }
    class ExplainabilityAgent {
        +investigate(state) state
    }

    GraphAgent ..> FraudInvestigationState : reads/writes
    TemporalAgent ..> FraudInvestigationState : reads/writes
    BehavioralAgent ..> FraudInvestigationState : reads/writes
    RiskFusionAgent ..> FraudInvestigationState : reads/writes
    ExplainabilityAgent ..> FraudInvestigationState : reads/writes
```

### 5.3 How each node scores (multi-step reasoning)

```mermaid
flowchart LR
    subgraph G["GraphAgent"]
        G1["Neo4j: relay/fan-out/hop-2 queries"] --> G2["GraphSAGE GNN embedding<br/>sigmoid(mean)"]
        G2 --> G3["graph_score = rules + 0.4*similarity"]
    end
    subgraph T["TemporalAgent"]
        T1["dormancy_break_flag +0.5"] --> T2["velocity_1h>5 +0.3"]
        T2 --> T3["LSTM AE anomaly correlate +0.2"]
    end
    subgraph B["BehavioralAgent"]
        B1["1h/24h velocity tiers"] --> B2["|amount_zscore|>3 +0.3"]
        B2 --> B3["new beneficiary + high amount +0.4"]
    end
    subgraph F["RiskFusionAgent"]
        F1["0.4·graph + 0.3·temporal + 0.3·behavioral"] --> F2{"score band"}
        F2 -->|>0.8| V1["mule_confirmed"]
        F2 -->|>0.4| V2["suspicious"]
        F2 -->|else| V3["cleared"]
    end
    G3 --> F1
    T3 --> F1
    B3 --> F1
```

### 5.4 Async execution wiring

```mermaid
sequenceDiagram
    autonumber
    participant UI
    participant API as investigations.py
    participant BG as FastAPI BackgroundTasks
    participant ORCH as FraudOrchestrator<br/>(LangGraph compiled)
    participant DB as SQLite

    UI->>API: POST /investigate?txn_id&account_id
    API->>DB: INSERT investigation (status=processing)
    API->>BG: add_task(run_task)
    API-->>UI: {investigation_id} (immediate)
    BG->>ORCH: workflow.invoke(initial_state)
    ORCH->>ORCH: graph→temporal→behavioral→fusion→[reg]→explain
    ORCH-->>BG: final state (score, verdict, narrative)
    BG->>DB: UPDATE status=completed, result=JSON
    UI->>API: GET /investigate/{id} (poll)
    API-->>UI: merged result
```

---

## 6. Mule Intelligence Subsystem (Deterministic Analytics)

**Files:** `src/mule_intelligence/*.py` · **Endpoints:** `GET/POST /api/v1/mule/*`

Not an LLM agent — a suite of deterministic graph/flow analytics over the SQLite ledger. It feeds
features into the other agents and powers the dashboards.

```mermaid
graph TB
    subgraph Mule["Mule Intelligence (Python, SQLite)"]
        PAT["MulePatternEvaluator<br/>8 pattern indicators<br/>GET /mule/patterns/{id}"]
        FLOW["MoneyFlowTracer<br/>upstream/downstream hops<br/>GET /mule/trace/{id}/*"]
        NET["NetworkRiskPropagator<br/>contagion propagation<br/>GET /mule/network-risk<br/>GET /mule/contamination/{id}"]
        EWS["EarlyWarningSystem<br/>batch EWS scoring<br/>GET /mule/ews/alerts<br/>POST /mule/ews/scan"]
        TRAIN["Model training trigger<br/>XGBoost + GraphSAGE + LSTM AE<br/>POST /mule/models/train<br/>(subprocess + thread)"]
    end
    SQLITE[(SQLite Core Ledger<br/>accounts, transactions,<br/>mule_accounts)]
    PAT --> SQLITE
    FLOW --> SQLITE
    NET --> SQLITE
    EWS --> SQLITE
    TRAIN -.spawns.-> SUB["scripts/train_models.py<br/>(.venv subprocess)"]
```

- **Model training** is launched as a background **subprocess** (`scripts/train_models.py`) under a
  daemon thread, streaming logs into an in-memory `training_state` polled via `GET /mule/models/status`.
- These analytics produce the `gnn_score`, `lstm_score`, and SHAP features later consumed by the
  Fraud Investigation Agent (§3).

---

## 7. Legal Intelligence Agent (External Enrichment)

**File:** `src/agents/legal_intelligence_agent.py` — invoked **inside** the COBOL Sentinel flow (§4, step ④).

```mermaid
flowchart TD
    START["enrich(context)"] --> Q{"Quota available?<br/>max 2 calls/day"}
    Q -->|Redis path| RQ["Redis INCR ecourts_quota:{date}<br/>expire 24h"]
    Q -->|Redis down| SQ["SQLite legal_quota_limit fallback"]
    SQ -->|SQLite down| MQ["In-memory global fallback"]
    Q -->|exhausted| LOW["Return LOW confidence,<br/>internal intelligence only"]

    RQ --> CALL["GET eCourts /api/partner/search<br/>?litigants={holder_name}<br/>Bearer partner_token, timeout 5s"]
    CALL --> SCORE["Classify cases:<br/>fraud (420/cheat/forgery)<br/>cyber (IT Act/phishing)<br/>→ legal_risk_score, confidence"]
    SCORE -->|no API match| MOCK["Correlate known-mule heuristics<br/>(mule_accounts table / id patterns)"]
    SCORE --> RET["Return court_matches,<br/>fraud/cyber counts, score, logs"]
    MOCK --> RET
```

**Three-tier quota fallback** (Redis → SQLite → in-memory) keeps the agent resilient when
infrastructure is partially down, while strictly capping the paid eCourts API at 2 calls/day.

---

## 8. Cross-Cutting Concerns

### 8.1 Groq API integration summary

| Aspect | Fraud Investigation Agent | COBOL Sentinel (extraction) |
|---|---|---|
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` | same |
| Model | `llama-3.3-70b-versatile` | `llama-3.3-70b-versatile` |
| Temperature | `0.2` (some creativity for prose) | `0.0` (deterministic parsing) |
| Output | `json_object` → `{summary_report, pdf_markdown}` | `json_object` → `{victim, mules, amount, cluster}` |
| Auth | `Authorization: Bearer {GROQ_API_KEY}` (env var + fallback) | same |
| Transport | raw `requests.post` (no SDK; OpenAI-compatible schema) | same |
| Timeout | 45s | 20s |
| Decision role | Writes the report | Parses entities only — **never decides** |

> ⚠️ **Security note:** both routers fall back to a **hard-coded `gsk_...` key** if `GROQ_API_KEY`
> is unset. This key is committed in source and should be moved to environment-only configuration
> and rotated.

### 8.2 Rate limiting / cost control across agents

```mermaid
graph LR
    A["Fraud Investigation Agent<br/>10 runs/day<br/>agent_rate_limit"] 
    B["COBOL Sentinel<br/>45 runs/day<br/>cobol_rate_limit"]
    C["Legal Intelligence<br/>2 calls/day<br/>Redis→SQLite→memory"]
    A & B & C --> NOTE["All counters keyed by date,<br/>enforced server-side,<br/>persisted in SQLite/Redis"]
```

### 8.3 Multi-step agentic process — the unifying pattern

```mermaid
graph TD
    INPUT["Input (ticket / txn / telemetry)"] --> EXTRACT
    EXTRACT["Step 1 — Extract / ingest<br/>(LLM parse OR feature load)"] --> ENRICH
    ENRICH["Step 2 — Enrich<br/>(SQLite ledger, Neo4j, eCourts, ML models)"] --> SCORE
    SCORE["Step 3 — Score<br/>(deterministic weighted fusion / COBOL rules)"] --> DECIDE
    DECIDE["Step 4 — Decide<br/>(verdict / HOLD-ALLOW / SAR flag)"] --> EXPLAIN
    EXPLAIN["Step 5 — Explain & persist<br/>(narrative, PDF, audit trail)"] --> OUTPUT["Output + downloadable evidence"]
```

Every agent in the platform — generative, stateful-graph, or hybrid-mainframe — follows this same
**extract → enrich → score → decide → explain** spine. The key architectural discipline is that
**LLMs participate only in the extract and explain steps**, while **scoring and deciding remain
deterministic** (Python fusion + COBOL rules), guaranteeing auditable, reproducible banking actions.

---

## 9. File Reference Map

| Concern | File |
|---|---|
| LangGraph orchestrator | `src/agents/orchestrator.py` |
| Shared agent state | `src/agents/state.py` |
| Specialist agents | `src/agents/{graph,temporal,behavioral,risk_fusion,explainability}_agent.py` |
| Legal Intelligence Agent | `src/agents/legal_intelligence_agent.py` |
| PDF report generator | `src/agents/pdf_generator.py` |
| Fraud Investigation Agent (Groq) | `src/api/routers/fraud_agent.py` |
| COBOL Sentinel router (Groq + Kafka) | `src/api/routers/cobol_sentinel.py` |
| COBOL Kafka bridge daemon | `src/cobol/sentinel_bridge.py` |
| COBOL rules engine | `src/cobol/SENTINEL.cbl` |
| Investigation API | `src/api/routers/investigations.py` |
| Mule Intelligence API | `src/api/routers/mule_intelligence.py` |
| Mule analytics modules | `src/mule_intelligence/{patterns,money_flow_tracer,network_scorer,early_warning}.py` |
| SQLite data bridge | `src/pipeline/cobol_bridge.py` |
| Router registration | `src/api/main.py` |
```
