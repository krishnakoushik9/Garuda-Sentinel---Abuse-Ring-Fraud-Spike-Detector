/* ═══════════════════════════════════════════════════════════════
   API TYPE DEFINITIONS — Mirrors backend Pydantic schemas
   ═══════════════════════════════════════════════════════════════ */

// ── Transactions ──
export interface Transaction {
  transaction_id: string;
  timestamp: string;
  sender_account: string;
  receiver_account: string;
  amount: number;
  channel: string;
  status: string;
  description?: string;
  risk_score: number;
}

export interface TransactionStats {
  total_count: number;
  fraud_count: number;
  mule_count: number;
  avg_risk_score: number;
}

// ── Accounts ──
export interface AccountProfile {
  account_id: string;
  name: string;
  customer_segment: string;
  city: string;
  state?: string;
  risk_profile: string;
  balance: number;
  pagerank?: number;
  community_id?: string;
  status?: string;
  recent_transactions?: Transaction[];
}

// ── Graph ──
export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphNeighborhood {
  nodes: GraphNode[];
  edges: GraphEdge[];
  is_offline?: boolean;
}

export interface CommunityGraphData {
  nodes: CommunityNode[];
  edges: CommunityEdge[];
}

export interface CommunityNode {
  account_id: string;
  name: string;
  risk_profile: string;
  status: string;
  pagerank: number;
  propagated_risk_score: number;
  community_id: string;
}

export interface CommunityEdge {
  id: string;
  source: string;
  target: string;
  amount: number;
  channel: string;
  risk_score: number;
  timestamp: string;
}

export interface FraudRing {
  community_id: string;
  avg_risk: number;
  size: number;
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  total_communities: number;
  mule_suspected_count: number;
  is_offline: boolean;
}

// ── Alerts ──
export interface Alert {
  id: string;
  transaction_id: string;
  account_id: string;
  fraud_type: string;
  severity: string;
  timestamp: string;
  amount?: number;
  risk_score?: number;
  channel?: string;
  description?: string;
}

// ── Dashboard ──
export interface DashboardSummary {
  total_accounts: number;
  total_transactions: number;
  high_risk_count: number;
  mule_count: number;
  top_fraud_patterns: FraudPattern[];
  recent_alerts: Alert[];
  graph_stats: {
    communities: number;
    neo4j_online: boolean;
  };
}

export interface FraudPattern {
  fraud_type: string;
  count: number;
}

// ── Investigations ──
export interface Investigation {
  id: string;
  account_id: string;
  status: 'processing' | 'completed' | 'failed';
  created_at: string;
  txn_id?: string;
  verdict?: string;
  final_risk_score?: number;
  explanation?: string;
  graph_findings?: string[];
  shap_values?: Record<string, number>;
}

// ── Regulatory ──
export interface RegulatoryNews {
  title: string;
  link: string;
  source: string;
  published: string;
  risk_score: number;
  risk_category: string;
  description?: string;
}

export interface WatchlistAccount {
  account_id: string;
  name: string;
  customer_segment: string;
  risk_profile: string;
  city: string;
  source: string;
  reason: string;
}

export interface WatchlistResponse {
  stats: Record<string, number>;
  watchlist: WatchlistAccount[];
}

export interface STR {
  str_id: string;
  account_id: string;
  transaction_ids: string[];
  fraud_type: string;
  amount: number;
  status: string;
  generated_at: string;
  narrative?: string;
}

export interface RFAAccount {
  account_id: string;
  name: string;
  risk_profile: string;
  reason: string;
  evidence: string;
  flagged_date: string;
  crilc_report_deadline: string;
  crilc_reported: number;
  fraud_classification_deadline: string;
  classification: string;
}

export interface RFAResponse {
  rfa_accounts: RFAAccount[];
  overdue_crilc_count: number;
  pending_classifications_count: number;
  overdue_crilc_accounts: string[];
  pending_classifications_accounts: string[];
}

// ── Government Data Intelligence ──
export interface GovDataStatus {
  last_ingested: Record<string, string | null>;
  record_counts: Record<string, number>;
  freshness_minutes: Record<string, number | null>;
  data_source: string;
  use_real_govdata: boolean;
}

export interface UpiBaselinePoint {
  month: string;
  volume_mn_transactions: number;
  value_cr_rupees: number;
  mom_change_pct: number;
  ingested_at?: string;
}

export interface GovUpiBaseline {
  monthly_avg_mn_transactions: number;
  daily_avg_mn_transactions: number;
  velocity_spike_threshold_mn_transactions: number;
  monthly_avg_value_cr_rupees: number;
  series: UpiBaselinePoint[];
  last_ingested: string | null;
  source_resource: string;
}

export interface GovFraudRecord {
  year: string;
  fraud_category: string;
  num_cases: number;
  amount_lakh: number;
  bank_type: string;
}

export interface GovFraudContext {
  fraud_category: string;
  year: string | null;
  num_cases_this_year: number;
  national_avg_fraud_amount_lakh: number;
  national_avg_fraud_amount_rupees: number;
  transaction_amount_rupees: number;
  percentile_rank: number;
  source: string;
  source_resource: string;
  records: GovFraudRecord[];
}

export interface GovGeoRiskRow {
  rank: number;
  state: string;
  latest_year: string;
  total_cases: number;
  risk_delta: number;
}

export interface GovGeoRisk {
  rankings: GovGeoRiskRow[];
  top_5_states: string[];
  source_resource: string;
}

export type GovRefreshResult = Record<string, { resource: string; records: number; signals?: number; status: string; error?: string }>;

// ── Mule Intelligence ──
export interface MulePattern {
  triggered: boolean;
  score: number;
  details: string;
}

export interface MulePatternResponse {
  account_id: string;
  triggered_patterns_count: number;
  patterns: Record<string, MulePattern>;
}

export interface MoneyFlowTrace {
  account_id: string;
  trace_type: 'DOWNSTREAM_FLOW' | 'UPSTREAM_FLOW';
  narrative?: string;
  flow_graph: {
    nodes: FlowNode[];
    edges: FlowEdge[];
  };
}

export interface FlowNode {
  id: string;
  hop: number;
  amount_received: number;
  risk_score?: number;
}

export interface FlowEdge {
  source: string;
  target: string;
  amount: number;
  channel?: string;
}

export interface NetworkRiskEntry {
  account_id: string;
  propagated_risk_score: number;
  name: string;
  risk_profile: string;
  status: string;
}

export interface EWSAlert {
  account_id: string;
  ews_score: number;
  triggered_signals: string[];
  name?: string;
}

// ── Cross-Channel ──
export interface ChannelProfile {
  account_id: string;
  profile: Record<string, ChannelUsage>;
  velocity: Record<string, number>;
}

export interface ChannelUsage {
  count: number;
  total_amount: number;
  avg_amount: number;
  dominance: number;
}

export interface ChannelHopAlert {
  account_id: string;
  channels_used: string[];
  hop_count: number;
  time_window_minutes: number;
  risk_level: string;
}

export interface InterBankFeed {
  authority: string;
  inter_bank_alert: Record<string, unknown>;
  npci_blacklisted_vpas: Record<string, unknown>[];
}

export interface UnifiedRiskScore {
  account_id: string;
  unified_score: number;
  breakdown: Record<string, number>;
  recommendation: string;
}

// ── System Status ──
export interface SystemStatus {
  cobol: 'online' | 'offline';
  fraudEngine: 'online' | 'offline';
  kafka: 'online' | 'offline';
  database: 'online' | 'offline';
}
