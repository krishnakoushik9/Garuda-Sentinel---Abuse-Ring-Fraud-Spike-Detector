# PS2 Mule Intelligence Layer Walkthrough

This document registers the architecture, components, and verified test execution traces of the **Mule Intelligence Layer** for the PS2 Fraud Intelligence Platform. 

---

## 1. Architectural System Overview

This subsystem detects, isolates, and actively traces the flow of illicit proceeds moving through mule account rings in order to enforce strict compliance with Section 12 PMLA and RBI Master Directions 2024.

```mermaid
graph TD
    subgraph Suspect Mule Core
        Suspect["Target suspect account_id"] --> PatEval["Mule Pattern Evaluator"]
        PatEval -->|8 criteria rules| Triggers["Pattern Matches / Threat probability"]
    end

    subgraph Fund Flow Analytics (Tracing)
        Suspect -->|Downstream BFS| DFlow["Downstream Flow Tracer"]
        DFlow -->|Classify Terminals| CashOut["Terminal Cash-out Points"]
        
        Suspect -->|Upstream Reverse BFS| UFlow["Upstream Source Tracer"]
        UFlow -->|Uncover source| FraudSource["Fraud Origin Seeds"]
    end

    subgraph Network Threat Contagion (PPR)
        Mules["Known Mule Seeds"] --> PPR["Personalized PageRank Propagation"]
        PPR -->|Hop-1 & Hop-2 Contagion| ThreatGraph["Infected Risk Mapping (>0.3)"]
    end

    subgraph Early Warning Signals (EWS)
        Core["Active Accounts Stream"] --> EWS["RBI Early Warning System"]
        EWS -->|5 weighted indicator vectors| CompositeEWS["Composite Alert Score"]
        CompositeEWS -->|Score >= 0.6| Alert["Actionable Pre-Mule Threat Alert"]
    end
```

---

## 2. Subsystem File Registry

All components are structured under the `src/mule_intelligence/` directory:

| Component Name | File Path | Detection / Tracing Task | Resilient Failsafe / Performance |
| :--- | :--- | :--- | :--- |
| **8 Patterns Specs** | [`patterns.py`](file:///home/krsna/Desktop/BOI/src/mule_intelligence/patterns.py) | Defines the 8 spec-mandated mule structures (RELAY_CHAIN, FAN_OUT, LAYERING, DORMANCY_BREAK, STRUCTURING, VELOCITY_SPIKE, NIGHT_ACTIVITY, ROUND_TRIP). | Runs Cypher graph queries on Neo4j. If offline, runs **local relational fallbacks on SQLite** using windowed time-hop matching. |
| **Money Flow Tracer** | [`money_flow_tracer.py`](file:///home/krsna/Desktop/BOI/src/mule_intelligence/money_flow_tracer.py) | Traces inflows back to fraud source (upstream) and outflows down to final cash-out terminals (downstream BFS). | Generates a narrative summary report suitable for FIU STR reporting. Uses an offline BFS memory traversal fallback. |
| **Network Risk Scorer** | [`network_scorer.py`](file:///home/krsna/Desktop/BOI/src/mule_intelligence/network_scorer.py) | Propagates network contamination levels using Personalized PageRank in Neo4j GDS. | Caches a recursive BFS network infection model on SQLite to ensure hop-1 and hop-2 neighbors receive scores $> 0.3$ offline. |
| **Early Warning System** | [`early_warning.py`](file:///home/krsna/Desktop/BOI/src/mule_intelligence/early_warning.py) | Implements the RBI EWS framework using 5 weighted indicators (KYC updates, high-value device swaps, cluster growth, inbound history spikiness). | Triggers preemptive actionable alerts for composite scores $\ge 0.6$. Runs nightly scans. |
| **FastAPI Controller** | [`mule_intelligence.py`](file:///home/krsna/Desktop/BOI/src/api/routers/mule_intelligence.py) | Exposes endpoints for patterns, flow tracing, PageRank contagion scores, and EWS scanning. | Clean routing logic mounted directly onto the central app instance. |

---

## 3. Verified Execution & Verification Results

### 1. In-line Spec Check
We verified the exact patterns loads dynamically under Python:
```bash
PYTHONPATH=. .venv/bin/python3 -c "from src.mule_intelligence.patterns import MULE_PATTERNS; print(len(MULE_PATTERNS), 'patterns loaded')"
```
**Output**:
```text
8 patterns loaded
```

### 2. Comprehensive Automated Smoke Test
We verified the complete Mule Intelligence REST ecosystem by running our custom test suite:
```bash
PYTHONPATH=.:.venv/lib/python3.12/site-packages python3 scripts/test_mule_intelligence.py
```
**All tests passed successfully**:
```text
==================================================
      PS2 MULE DETECTION INTELLIGENCE SMOKE TEST
==================================================
Using suspect account for testing: ACC000001

[PASS] Mule Patterns Evaluator (GET /patterns/{id})       Triggered: 0/8 patterns.
[PASS] Downstream Flow Tracer (GET /trace/{id}/downstream) Traced 8505 nodes, 13754 flow paths. Total: ₹907,089,314.54
[PASS] Upstream Flow Tracer (GET /trace/{id}/upstream)    Traced 30 nodes, 29 flow paths back to source.
[PASS] Network Risk Contagion Scorer (GET /network-risk)  Fetched top 50 infected accounts.
[PASS] EWS Active Alerts Fetcher (GET /ews/alerts)        Fetched 2 active EWS alerts.
[PASS] EWS Batch Scan Trigger (POST /ews/scan)            Scanned 100 accounts, found 2 actionable pre-mules.
[PASS] Contamination Radius Evaluator (GET /contamination/{id}) Suspect node threat propagation radius: 1734 accounts.

==================================================
ALL MULE INTELLIGENCE ENDPOINTS ARE FUNCTIONAL // PASS
```
