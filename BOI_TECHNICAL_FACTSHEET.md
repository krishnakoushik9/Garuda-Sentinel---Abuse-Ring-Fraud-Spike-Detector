# BOI Fraud Detection Platform: Technical Fact Sheet
## Graph/GNN and Mule Intelligence Subsystems

---

## 1. GRAPH NEURAL NETWORK ARCHITECTURE

### Framework & Model Type
- **Framework**: PyTorch Geometric (PyG)
- **Base Architecture**: Temporal GNN with TransformerConv (NOT standard GraphSAGE as originally indicated)
- **File Location**: `src/ml/models/gnn_model.py`

### Network Topology (MuleDetectionGNN class)
**Layer Configuration** (`gnn_model.py:25-46`):
- **Input channels**: 12 (node feature dimensionality)
- **Hidden channels**: 64
- **Output channels**: 2 (binary classification: mule/non-mule)
- **Edge dimension**: 3 (amount, channel_encoded, velocity)
- **Time embedding dimension**: 64

**Exact Layer Sequence** (`gnn_model.py:39-46`):
```python
Layer 1: TransformerConv(in_channels=12, hidden_channels=64, heads=2, concat=True, edge_dim=64)
         → Output: 128 (64 * 2 concat)
         → BatchNorm1d(128)
         → ReLU + Dropout(0.3)

Layer 2: TransformerConv(in_channels=128, hidden_channels=64, heads=2, concat=True, edge_dim=64)
         → Output: 128 (64 * 2 concat)
         → BatchNorm1d(128)
         → ReLU + Dropout(0.3)

Layer 3: TransformerConv(in_channels=128, out_channels=2, heads=1, concat=False, edge_dim=64)
         → Output: 2
         → Log Softmax (dim=1)
```

### Time Encoding Module
**TimeEncoder** (`gnn_model.py:6-23`):
- Maps edge timestamps to 64-dimensional periodic sine embeddings
- Learnable frequency weights: `w ∈ ℝ^{1×64}`
- Learnable phase bias: `b ∈ ℝ^{1×64}`
- Formula: `sin(t * w + b)` where t is timestamp

### Training Setup
**File**: `src/ml/train_gnn.py`

**Training Hyperparameters** (`train_gnn.py:67, 70-72`):
- **Optimizer**: Adam (lr=0.01, weight_decay=1e-4)
- **Loss function**: NLLLoss (Negative Log Likelihood)
- **Class weights**: [1.0, 50.0] (50x penalty for mule class to handle extreme imbalance)
- **Epochs**: 20 (configurable in `train_temporal_gnn()`)
- **Batch size**: 2048
- **Device**: Auto-detect GPU if available, fallback to CPU

**Sampling Strategy** (`train_gnn.py:57-64`):
- **NeighborLoader** from PyTorch Geometric
- **Neighbor samples per hop**: [15, 10] (1st hop: 15 neighbors, 2nd hop: 10 neighbors)
- **Temporal sampling**: `time_attr='timestamp'` enforces chronological ordering
- **Input nodes**: All nodes sampled (input_nodes=None)
- **Shuffle**: True

### Node Feature Vectors
**12-dimensional feature vector** (`graph_builder.py:41-62`):
```
f0:  amount_zscore
f1:  is_new_beneficiary
f2:  fan_out_ratio
f3:  dormancy_break_flag
f4:  night_txn_ratio
f5:  txn_velocity_1h
f6:  txn_velocity_24h
f7:  txn_velocity_7d
f8:  unique_beneficiaries_7d
f9:  graph_degree_centrality
f10: suspicious_neighbor_count
f11: hop_2_mule_count
```

**Default initialization**: `torch.randn(num_nodes, 12)` with optional SQLite cache lookup (`transaction_features` table)

### Edge Attributes
**3-dimensional edge feature vector** (`graph_builder.py:119`):
```
[amount, channel_encoded, time_since_last_transaction]
```

**Channel encoding** (8 payment channels, `graph_builder.py:9-18`):
```
UPI: 0.0, IMPS: 1.0, NEFT: 2.0, RTGS: 3.0,
CARD: 4.0, ATM: 5.0, MERCHANT: 6.0, WALLET: 7.0
```

---

## 2. NEO4J GRAPH SCHEMA & RELATIONSHIPS

### Node Types
**Confirmed in codebase** (`neo4j_loader.py:34-41`, `seed_neo4j.py`):

| Node Type | Label | Properties | Source |
| --- | --- | --- | --- |
| Account | `:Account` | account_id, name, segment, city, risk_profile | neo4j_loader.py:36 |

**Additional Properties Written by GDS Analytics** (`seed_neo4j.py:35-45`):
- `community_id`: Louvain clustering result
- `pagerank`: PageRank centrality score

### Edge/Relationship Types
**Single relationship type confirmed** (`neo4j_loader.py:75`, `seed_neo4j.py:28`):

| Relationship | Cypher | Properties | Semantics |
| --- | --- | --- | --- |
| SENT_TO | `(Account)-[:SENT_TO]→(Account)` | amount, timestamp, channel, transaction_id | Directional money flow from sender to receiver |

**Edge Properties** (`neo4j_loader.py:76-78`):
```
amount: transaction amount (float)
timestamp: ISO datetime string
channel: UPI/IMPS/NEFT/RTGS/CARD/ATM/MERCHANT/WALLET
transaction_id: unique transaction identifier
```

### Schema Notes
**No explicit node types**: The schema only materializes `:Account` nodes. Device, IP, Merchant nodes are NOT found in the codebase—only transaction graph between accounts exists.

### Graph Projection (GDS)
**Projection name**: `'fraud_graph'` (`seed_neo4j.py:25-30`)
```
Project(
  'fraud_graph',
  nodeLabel='Account',
  relationshipType='SENT_TO',
  relationshipProperties='amount'
)
```

---

## 3. ACTUAL CYPHER QUERIES FOR MULE RING DETECTION

### Query 1: RELAY_CHAIN (Sequential Money Forwarding)
**Pattern Name**: RELAY_CHAIN  
**Probability**: 0.89  
**File**: `src/mule_intelligence/patterns.py:11-18`

```cypher
MATCH path = (source:Account)-[:SENT_TO*2..5]->(cashout:Account)
WHERE source.id = $account_id
AND ALL(r IN relationships(path) WHERE 
    duration.inSeconds(r.timestamp, r.next_timestamp).seconds < 3600
    AND r.amount >= r.prev_amount * 0.7)
RETURN path, length(path) as chain_length
ORDER BY chain_length DESC LIMIT 10
```
**Description**: 2–5 hop chain within 1 hour, each hop preserves ≥70% amount

### Query 2: FAN_OUT (Multiple Receivers from Few Sources)
**Pattern Name**: FAN_OUT  
**Probability**: 0.85  
**File**: `src/mule_intelligence/patterns.py:24-34`

```cypher
MATCH (mule:Account {id: $account_id})-[r:SENT_TO]->(dest:Account)
WHERE r.timestamp > datetime() - duration('P7D')
WITH mule, COUNT(DISTINCT dest) as dest_count, SUM(r.amount) as total_out
MATCH (src:Account)-[:SENT_TO]->(mule)
WITH mule, dest_count, total_out, COUNT(DISTINCT src) as src_count
WHERE dest_count > 5 AND src_count <= 2
RETURN mule.id, dest_count, src_count, total_out
```
**Description**: 1–2 inbound sources → 5+ outbound destinations in last 7 days

### Query 3: LAYERING (Intermediate Pass-through Hops)
**Pattern Name**: LAYERING  
**Probability**: 0.78  
**File**: `src/mule_intelligence/patterns.py:37-49`

```cypher
MATCH (origin:Account)-[:SENT_TO*1..4]->(layer:Account)
WHERE origin.id = $account_id
WITH DISTINCT layer, 
     SIZE([(layer)-[:SENT_TO]->() | 1]) as out_degree,
     SIZE([()-[:SENT_TO]->(layer) | 1]) as in_degree
WHERE out_degree > 0 AND in_degree > 0
AND abs(out_degree - in_degree) < 2
RETURN layer.id, out_degree, in_degree
ORDER BY out_degree DESC
```
**Description**: Multiple intermediate accounts with balanced in/out degree (±1)

### Query 4: ROUND_TRIP (Circular Money Return)
**Pattern Name**: ROUND_TRIP  
**Probability**: 0.91  
**File**: `src/mule_intelligence/patterns.py:96-101`

```cypher
MATCH (a:Account {id: $account_id})-[:SENT_TO*2..6]->(a)
RETURN COUNT(*) as cycle_count
```
**Description**: 2–6 hop cycles that return to origin account (highest mule probability)

### Hop Traversal Details
**Downstream Trace** (BFS, up to 6 hops):  
`src/mule_intelligence/money_flow_tracer.py:34-39`
```cypher
MATCH path = (start:Account {id: $account_id})-[:SENT_TO*1..6]->(end:Account)
RETURN [n IN nodes(path) | n.id] as node_ids,
       [r IN relationships(path) | {amount: r.amount, channel: r.channel, timestamp: r.timestamp}] as rels
LIMIT 50
```

**Upstream Trace** (Reverse BFS, up to 4 hops):  
Similar pattern but traversing backwards via `<-[:SENT_TO]-` to find source.

### Risk Propagation Query (Personalized PageRank)
**File**: `src/mule_intelligence/network_scorer.py:33-46`

```cypher
CALL gds.pageRank.stream('fraud_graph', {
    maxIterations: 20,
    dampingFactor: 0.85,
    sourceNodes: [
        (a:Account) WHERE a.id IN $known_mules | id(a)
    ]
})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS account, score
WHERE score > 0.01
SET account.propagated_risk = score
RETURN account.id as id, score
ORDER BY score DESC
```
**Parameters**:
- Max iterations: 20
- Damping factor: 0.85 (standard PageRank coefficient)
- Source nodes: Known mule seeds
- Filter threshold: score > 0.01

---

## 4. MULE HEURISTICS & DETECTION PATTERNS

### 8 Core Mule Patterns

| Pattern | Type | Trigger Condition | Probability | Source |
| --- | --- | --- | --- | --- |
| **RELAY_CHAIN** | Cypher Graph | 2–5 hop chain, <1hr, 70%+ amount preserved | 0.89 | patterns.py:11 |
| **FAN_OUT** | Cypher Graph | 1–2 senders → 5+ receivers (7 days) | 0.85 | patterns.py:24 |
| **LAYERING** | Cypher Graph | Intermediate accounts, balanced in/out degree | 0.78 | patterns.py:37 |
| **DORMANCY_BREAK** | SQL | 30+ days dormant → activation ₹10k+, within 7 days | 0.78 | patterns.py:51 |
| **STRUCTURING** | SQL | 3+ txns in 24h, each ₹40k–₹49,999 (just below ₹50k threshold) | 0.72 | patterns.py:70 |
| **VELOCITY_SPIKE** | SQL | Txn count today > mean_daily + 5σ, and > 3 txns | 0.81 | patterns.py:87 |
| **NIGHT_ACTIVITY** | SQL | 60%+ transactions between 23:00–05:00 | 0.65 | patterns.py:91 |
| **ROUND_TRIP** | Cypher Graph | 2–6 hop cycle returning to origin | 0.91 | patterns.py:96 |

### Velocity Checks
**24-hour transaction velocity** (from node feature `f5`):
- SQL Query: `COUNT(*) FROM transactions WHERE sender_account = ? AND timestamp > datetime('now', '-1 day')`
- Trigger: `velocity_24h > (mean_daily_30d + 5)` AND `count > 3`
- File: `patterns.py:140-160`

### Dormancy Detection
**30+ day gap with activation spike**:  
```sql
SELECT a.account_id, 
       MAX(t1.timestamp) as last_old_txn,
       MIN(t2.timestamp) as first_new_txn,
       julianday(MIN(t2.timestamp)) - julianday(MAX(t1.timestamp)) as dormant_days,
       SUM(t2.amount) as activation_amount
FROM accounts a
JOIN transactions t1 ON t1.sender_account = a.account_id 
    AND t1.timestamp < datetime('now', '-30 days')
JOIN transactions t2 ON t2.sender_account = a.account_id 
    AND t2.timestamp > datetime('now', '-7 days')
WHERE a.account_id = ?
GROUP BY a.account_id
HAVING dormant_days > 30 AND activation_amount > 10000
```
**File**: `patterns.py:52-66`

### Structuring Detection
**Threshold layering just below ₹50,000 AML reporting limit**:
```sql
SELECT sender_account, COUNT(*) as txn_count, SUM(amount) as total,
       MAX(amount) as max_single, AVG(amount) as avg_amount
FROM transactions
WHERE sender_account = ?
AND timestamp > datetime('now', '-1 day')
AND amount BETWEEN 40000 AND 49999
GROUP BY sender_account
HAVING txn_count >= 3 AND max_single < 50000
```
**File**: `patterns.py:70-85`

### Money Flow Tracing Logic

**Downstream (Cash-out identification)**:
- BFS from suspect account, max 6 hops
- Classify terminal nodes (0 outbound edges) as "CASHOUT"
- Track amount_forwarded per node
- File: `money_flow_tracer.py:17-151`

**Upstream (Source identification)**:
- Reverse BFS from suspect, max 4 hops
- Classify terminal nodes (0 inbound edges) as "SOURCE"
- Track amount_in per node
- File: `money_flow_tracer.py:153-222`

### Network Centrality Scoring

**Personalized PageRank Propagation**:
- **Direct mule seed**: score = 1.0
- **1st-hop neighbors** (connected directly): score = 0.55
- **2nd-hop neighbors** (2 edges away): score = 0.35
- **Offline SQLite fallback**: recursive BFS risk contagion
- File: `network_scorer.py:18-97`

**Contamination Radius Calculation**:
```python
hop_1_count = distinct neighbors of account (both directions)
hop_2_count = distinct neighbors of hop-1 (excluding hop-1 and origin)
total_threat_radius = hop_1_count + hop_2_count
```
**File**: `network_scorer.py:99-146`

---

## 5. EARLY WARNING SYSTEM (RBI EWS Framework)

### 5 Weighted EWS Signals
**File**: `src/mule_intelligence/early_warning.py:14-35`

| Signal Name | Weight | Trigger Condition |
| --- | --- | --- |
| PRE_ACTIVATION_KYC_UPDATE | 0.4 | KYC changed within 7 days before high-value txn |
| NEW_DEVICE_HIGH_VALUE | 0.5 | First txn from new device ≥ ₹50,000 |
| BENEFICIARY_CLUSTER_GROWTH | 0.6 | Unique beneficiaries > 10/day or ≥3 in 3 days |
| INBOUND_SPIKE_NO_HISTORY | 0.7 | Large inbound (₹25k+) to account with <3 prior transactions |
| GEOGRAPHIC_ANOMALY | 0.45 | Govt-flagged status or location inconsistency |

### Composite EWS Score Calculation
**Formula** (`early_warning.py:134-136`):
```
ews_score = min(sum_of_triggered_weights, 1.0)
action_required = (ews_score >= 0.6)
```

### Batch EWS Scan
- Scans top 500 active accounts from SQLite
- Computes `compute_ews_score()` for each
- Returns alerts sorted by score descending
- Returns top N (limit parameter, default 100)
- File: `early_warning.py:151-177`

---

## 6. RISK SCORE COMPOSITION

### Combined Risk Scoring
**File**: `src/mule_intelligence/mule_intelligence.py` (API Router)

The platform composes risk from three channels:

1. **ML Model Score** (GNN binary classification):
   - Output: log_softmax over 2 classes (mule/non-mule)
   - Probability extracted from output logits

2. **Graph Centrality**:
   - PageRank propagated_risk_score (0–1)
   - Degree centrality (normalized)
   - Betweenness centrality (from GDS analytics)
   - Stored in `graph_analytics` table

3. **Regulatory Flag**:
   - Account status: GOVT_FLAGGED, RFA, ACTIVE
   - Risk profile: HIGH, MEDIUM, LOW
   - EWS composite score (0–1)
   - Pattern trigger count (0–8)

### Risk Score API Response Format
**Endpoint**: `GET /mule/network-risk`  
**Returns** (top 50): `mule_intelligence.py:78-122`
```json
{
  "account_id": "...",
  "propagated_risk_score": 0.85,
  "name": "...",
  "risk_profile": "HIGH",
  "status": "GOVT_FLAGGED"
}
```

---

## 7. TRANSACTION FEATURE ENGINEERING

**12 computed features for node representation**:

| Feature | Computation | SQL Source |
| --- | --- | --- |
| amount_zscore | (amount - μ) / σ | Dynamically computed |
| is_new_beneficiary | 1 if first txn to receiver | Transaction history |
| fan_out_ratio | (distinct_receivers) / (total_outgoing) | Last 7 days |
| dormancy_break_flag | 1 if 30+ day gap + spike | Transaction history |
| night_txn_ratio | % txns between 23:00–05:00 | Timestamp extraction |
| txn_velocity_1h | Count of txns in last hour | TIME-based grouping |
| txn_velocity_24h | Count of txns in last 24h | TIME-based grouping |
| txn_velocity_7d | Count of txns in last 7 days | TIME-based grouping |
| unique_beneficiaries_7d | Distinct receiver_account count (7d) | GROUP BY query |
| graph_degree_centrality | In-degree + out-degree normalized | GDS / Manual |
| suspicious_neighbor_count | Neighbors with risk_profile=HIGH | JOIN query |
| hop_2_mule_count | Neighbors 2 hops away marked as mules | BFS traversal |

**Feature cache table**: `transaction_features` (created dynamically in `feature_engineering.py:61-78`)

---

## 8. SUMMARY TABLE: FILES & COMPONENTS

| Component | File Path | Key Responsibility | Resilience |
| --- | --- | --- | --- |
| GNN Architecture | `src/ml/models/gnn_model.py` | Temporal TransformerConv-based mule classification | PyTorch standard |
| Training Pipeline | `src/ml/train_gnn.py` | NeighborLoader sampling, loss computation | Auto GPU fallback |
| Graph Builder | `src/pipeline/graph_builder.py` | PyG Data object construction, node/edge feature packaging | Graceful null handling |
| Neo4j Loader | `src/pipeline/neo4j_loader.py` | Batch seeding Account → Neo4j, SENT_TO relationships | Disabled mode if offline |
| GDS Seed Script | `scripts/seed_neo4j.py` | Louvain + PageRank projection and analytics write-back | Exception handling |
| 8 Mule Patterns | `src/mule_intelligence/patterns.py` | Cypher queries + SQL fallback for mule ring detection | Neo4j+Cypher or SQLite BFS |
| Money Flow Tracer | `src/mule_intelligence/money_flow_tracer.py` | Downstream/upstream BFS, cash-out/source identification | BFS memory traversal fallback |
| Network Scorer | `src/mule_intelligence/network_scorer.py` | PPR-based risk propagation, contamination radius | SQLite hop-1/hop-2 recursion |
| Early Warning | `src/mule_intelligence/early_warning.py` | RBI EWS 5-signal framework, pre-mule threat alerts | SQLite-native queries |
| Mule Intelligence API | `src/api/routers/mule_intelligence.py` | FastAPI endpoints for patterns, tracing, risk, EWS | Clean routing, error handling |
| Graph API | `src/api/routers/graph.py` | Community retrieval, fraud rings, GDS stats | SQLite + Neo4j optional |

---

## 9. EXECUTION VERIFICATION

**Confirmed working** (from MULE_INTELLIGENCE_LAYER.md smoke test):
- ✅ 8 mule patterns evaluate correctly
- ✅ Downstream flow tracing: 8,505 nodes, 13,754 paths, ₹907M total traced
- ✅ Upstream flow tracing: 30 nodes, 29 paths back to source
- ✅ Network risk contagion: top 50 infected accounts
- ✅ EWS batch scan: 100 accounts, 2 actionable pre-mule alerts (score ≥ 0.6)
- ✅ Contamination radius: 1,734 account threat propagation

