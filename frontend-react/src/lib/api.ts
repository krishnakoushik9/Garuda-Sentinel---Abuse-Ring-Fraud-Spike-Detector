/* ═══════════════════════════════════════════════════════════════
   API CLIENT — Centralized fetch layer for all backend endpoints
   ═══════════════════════════════════════════════════════════════ */

const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error ${res.status}`);
  }
  return res.json();
}

// ── Dashboard ──
export const dashboardApi = {
  getSummary: () => request<import('@/types/api').DashboardSummary>('/dashboard/summary'),
};

// ── Transactions ──
export const transactionsApi = {
  getAll: (params?: {
    page?: number;
    limit?: number;
    channel?: string;
    risk_tier?: string;
    account_id?: string;
    search?: string;
    min_amount?: number;
    max_amount?: number;
    status?: string;
    sort_by?: string;
    sort_order?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.set(key, String(value));
        }
      });
    }
    const qs = searchParams.toString();
    return request<import('@/types/api').Transaction[]>(`/transactions/${qs ? `?${qs}` : ''}`);
  },
  getById: (txnId: string) =>
    request<import('@/types/api').Transaction>(`/transactions/${txnId}`),
  getStats: () =>
    request<import('@/types/api').TransactionStats>('/transactions/stats'),
};

// ── Accounts ──
export const accountsApi = {
  getAll: (params?: { page?: number; limit?: number; risk_score_min?: number; community_id?: string; state?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) searchParams.set(key, String(value));
      });
    }
    const qs = searchParams.toString();
    return request<import('@/types/api').AccountProfile[]>(`/accounts/${qs ? `?${qs}` : ''}`);
  },
  getById: (accountId: string) =>
    request<import('@/types/api').AccountProfile>(`/accounts/${accountId}`),
  getGraph: (accountId: string) =>
    request<import('@/types/api').GraphNeighborhood>(`/accounts/${accountId}/graph`),
  flag: (accountId: string) =>
    request<{ status: string; message: string }>(`/accounts/${accountId}/flag`, { method: 'POST' }),
};

// ── Alerts ──
export const alertsApi = {
  getAll: () => request<import('@/types/api').Alert[]>('/alerts/'),
  streamUrl: `${BASE}/alerts/stream`,
  searchECourts: (query: string) => request<{ results: any[] }>(`/alerts/ecourts/search?query=${encodeURIComponent(query)}`),
  getECourtsCase: (cnr: string) => request<any>(`/alerts/ecourts/case/${cnr}`),
  trackECourtsCase: (cnr: string, accountId?: string) => request<{ status: string; message: string; correlated_account: any }>(`/alerts/ecourts/track`, {
    method: 'POST',
    body: JSON.stringify({ cnr, account_id: accountId })
  }),
};


// ── Graph ──
export const graphApi = {
  getCommunity: (communityId: string) =>
    request<import('@/types/api').CommunityGraphData>(`/graph/community/${communityId}`),
  getFraudRings: () =>
    request<import('@/types/api').FraudRing[]>('/graph/fraud-rings'),
  getStats: () =>
    request<import('@/types/api').GraphStats>('/graph/stats'),
};

// ── Investigations ──
export const investigationsApi = {
  start: (txnId: string, accountId: string) =>
    request<{ investigation_id: string }>(`/investigate?txn_id=${txnId}&account_id=${accountId}`, { method: 'POST' }),
  getById: (investigationId: string) =>
    request<import('@/types/api').Investigation>(`/investigate/${investigationId}`),
  getAll: () =>
    request<import('@/types/api').Investigation[]>('/investigate/'),
};

// ── Regulatory ──
export const regulatoryApi = {
  getNews: (query?: string) => {
    const qs = query ? `?query=${encodeURIComponent(query)}` : '';
    return request<import('@/types/api').RegulatoryNews[]>(`/regulatory/news${qs}`);
  },
  getWatchlist: () =>
    request<import('@/types/api').WatchlistResponse>('/regulatory/watchlist'),
  getSTRs: () =>
    request<import('@/types/api').STR[]>('/regulatory/strs'),
  fileSTR: (strId: string, analystId?: string) =>
    request<{ status: string; message: string }>(
      `/regulatory/strs/${strId}/file${analystId ? `?analyst_id=${analystId}` : ''}`,
      { method: 'POST' }
    ),
  getRFA: () =>
    request<import('@/types/api').RFAResponse>('/regulatory/rfa'),
  getAlertFeed: () =>
    request<Record<string, unknown>[]>('/regulatory/alerts/feed'),
  simulate: () =>
    request<Record<string, unknown>>('/regulatory/simulate', { method: 'POST' }),
};

// ── Government Data Intelligence ──
export const govdataApi = {
  getStatus: () =>
    request<import('@/types/api').GovDataStatus>('/govdata/status'),
  getUpiBaseline: () =>
    request<import('@/types/api').GovUpiBaseline>('/govdata/upi-baseline'),
  getFraudContext: (fraudCategory = 'UPI_FRAUD', amount = 0) =>
    request<import('@/types/api').GovFraudContext>(
      `/govdata/fraud-context?fraud_category=${encodeURIComponent(fraudCategory)}&amount=${amount}`
    ),
  getGeoRisk: () =>
    request<import('@/types/api').GovGeoRisk>('/govdata/geo-risk'),
  refresh: () =>
    request<import('@/types/api').GovRefreshResult>('/govdata/refresh', { method: 'POST' }),
};

// ── Mule Intelligence ──
export const muleApi = {
  getPatterns: (accountId: string) =>
    request<import('@/types/api').MulePatternResponse>(`/mule/patterns/${accountId}`),
  traceDownstream: (accountId: string, maxHops?: number) =>
    request<import('@/types/api').MoneyFlowTrace>(
      `/mule/trace/${accountId}/downstream${maxHops ? `?max_hops=${maxHops}` : ''}`
    ),
  traceUpstream: (accountId: string, maxHops?: number) =>
    request<import('@/types/api').MoneyFlowTrace>(
      `/mule/trace/${accountId}/upstream${maxHops ? `?max_hops=${maxHops}` : ''}`
    ),
  getNetworkRisk: () =>
    request<import('@/types/api').NetworkRiskEntry[]>('/mule/network-risk'),
  getEWSAlerts: () =>
    request<import('@/types/api').EWSAlert[]>('/mule/ews/alerts'),
  triggerEWSScan: (limit?: number) =>
    request<Record<string, unknown>>(`/mule/ews/scan${limit ? `?limit=${limit}` : ''}`, { method: 'POST' }),
  getContamination: (accountId: string) =>
    request<Record<string, unknown>>(`/mule/contamination/${accountId}`),
  trainModels: () =>
    request<{ status: string; message: string; started_at?: number }>('/mule/models/train', { method: 'POST' }),
  getTrainingStatus: () =>
    request<{ status: string; started_at: number | null; finished_at: number | null; logs: string[]; error: string | null }>('/mule/models/status'),
};

// ── Cross-Channel ──
export const crossChannelApi = {
  getProfile: (accountId: string) =>
    request<import('@/types/api').ChannelProfile>(`/cross-channel/profile/${accountId}`),
  getHopAlerts: () =>
    request<import('@/types/api').ChannelHopAlert[]>('/cross-channel/hop-alerts'),
  getChannelStats: () =>
    request<any[]>('/cross-channel/channel-stats'),
  getInterBank: () =>
    request<import('@/types/api').InterBankFeed>('/cross-channel/inter-bank'),
  getUnifiedScore: (accountId: string) =>
    request<import('@/types/api').UnifiedRiskScore>(`/cross-channel/unified-score/${accountId}`),
  simulateFeed: () =>
    request<Record<string, unknown>>('/cross-channel/simulate-feed', { method: 'POST' }),
};
