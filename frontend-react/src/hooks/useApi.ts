/* ═══════════════════════════════════════════════════════════════
   TANSTACK QUERY HOOKS — Typed data-fetching hooks for all APIs
   ═══════════════════════════════════════════════════════════════ */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  dashboardApi,
  transactionsApi,
  accountsApi,
  alertsApi,
  graphApi,
  investigationsApi,
  regulatoryApi,
  govdataApi,
  muleApi,
  crossChannelApi,
} from '@/lib/api';

// ── Dashboard ──
export const useDashboardSummary = () =>
  useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.getSummary,
    refetchInterval: 10000,
  });

// ── Transactions ──
export const useTransactions = (params?: Parameters<typeof transactionsApi.getAll>[0]) =>
  useQuery({
    queryKey: ['transactions', params],
    queryFn: () => transactionsApi.getAll(params),
  });

export const useTransaction = (txnId: string) =>
  useQuery({
    queryKey: ['transaction', txnId],
    queryFn: () => transactionsApi.getById(txnId),
    enabled: !!txnId,
  });

export const useTransactionStats = () =>
  useQuery({
    queryKey: ['transactions', 'stats'],
    queryFn: transactionsApi.getStats,
    refetchInterval: 15000,
  });

// ── Accounts ──
export const useAccounts = (params?: Parameters<typeof accountsApi.getAll>[0]) =>
  useQuery({
    queryKey: ['accounts', params],
    queryFn: () => accountsApi.getAll(params),
  });

export const useAccount = (accountId: string) =>
  useQuery({
    queryKey: ['account', accountId],
    queryFn: () => accountsApi.getById(accountId),
    enabled: !!accountId,
  });

export const useAccountGraph = (accountId: string) =>
  useQuery({
    queryKey: ['account', 'graph', accountId],
    queryFn: () => accountsApi.getGraph(accountId),
    enabled: !!accountId,
  });

export const useFlagAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) => accountsApi.flag(accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

// ── Alerts ──
export const useAlerts = () =>
  useQuery({
    queryKey: ['alerts'],
    queryFn: alertsApi.getAll,
    refetchInterval: 5000,
  });

// ── Graph ──
export const useCommunityGraph = (communityId: string) =>
  useQuery({
    queryKey: ['graph', 'community', communityId],
    queryFn: () => graphApi.getCommunity(communityId),
    enabled: !!communityId,
  });

export const useFraudRings = () =>
  useQuery({
    queryKey: ['graph', 'fraud-rings'],
    queryFn: graphApi.getFraudRings,
  });

export const useGraphStats = () =>
  useQuery({
    queryKey: ['graph', 'stats'],
    queryFn: graphApi.getStats,
  });

// ── Investigations ──
export const useInvestigations = () =>
  useQuery({
    queryKey: ['investigations'],
    queryFn: investigationsApi.getAll,
  });

export const useInvestigation = (id: string) =>
  useQuery({
    queryKey: ['investigation', id],
    queryFn: () => investigationsApi.getById(id),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === 'processing' ? 2000 : false,
  });

export const useStartInvestigation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ txnId, accountId }: { txnId: string; accountId: string }) =>
      investigationsApi.start(txnId, accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
    },
  });
};

// ── Regulatory ──
export const useRegulatoryNews = (query?: string) =>
  useQuery({
    queryKey: ['regulatory', 'news', query],
    queryFn: () => regulatoryApi.getNews(query),
  });

export const useWatchlist = () =>
  useQuery({
    queryKey: ['regulatory', 'watchlist'],
    queryFn: regulatoryApi.getWatchlist,
  });

export const useSTRs = () =>
  useQuery({
    queryKey: ['regulatory', 'strs'],
    queryFn: regulatoryApi.getSTRs,
  });

export const useFileSTR = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ strId, analystId }: { strId: string; analystId?: string }) =>
      regulatoryApi.fileSTR(strId, analystId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['regulatory', 'strs'] });
    },
  });
};

export const useRFA = () =>
  useQuery({
    queryKey: ['regulatory', 'rfa'],
    queryFn: regulatoryApi.getRFA,
  });

export const useRegulatorySimulate = () =>
  useMutation({
    mutationFn: regulatoryApi.simulate,
  });

// ── Government Data Intelligence ──
export const useGovDataStatus = () =>
  useQuery({
    queryKey: ['govdata', 'status'],
    queryFn: govdataApi.getStatus,
    refetchInterval: 60000,
  });

export const useGovUpiBaseline = () =>
  useQuery({
    queryKey: ['govdata', 'upi-baseline'],
    queryFn: govdataApi.getUpiBaseline,
  });

export const useGovFraudContext = () =>
  useQuery({
    queryKey: ['govdata', 'fraud-context'],
    queryFn: () => govdataApi.getFraudContext('UPI_FRAUD', 0),
  });

export const useGovGeoRisk = () =>
  useQuery({
    queryKey: ['govdata', 'geo-risk'],
    queryFn: govdataApi.getGeoRisk,
  });

export const useGovDataRefresh = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: govdataApi.refresh,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['govdata'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

// ── Mule Intelligence ──
export const useMulePatterns = (accountId: string) =>
  useQuery({
    queryKey: ['mule', 'patterns', accountId],
    queryFn: () => muleApi.getPatterns(accountId),
    enabled: !!accountId,
  });

export const useMoneyFlowDownstream = (accountId: string, maxHops?: number) =>
  useQuery({
    queryKey: ['mule', 'trace', 'downstream', accountId, maxHops],
    queryFn: () => muleApi.traceDownstream(accountId, maxHops),
    enabled: !!accountId,
  });

export const useMoneyFlowUpstream = (accountId: string, maxHops?: number) =>
  useQuery({
    queryKey: ['mule', 'trace', 'upstream', accountId, maxHops],
    queryFn: () => muleApi.traceUpstream(accountId, maxHops),
    enabled: !!accountId,
  });

export const useNetworkRisk = () =>
  useQuery({
    queryKey: ['mule', 'network-risk'],
    queryFn: muleApi.getNetworkRisk,
  });

export const useEWSAlerts = () =>
  useQuery({
    queryKey: ['mule', 'ews', 'alerts'],
    queryFn: muleApi.getEWSAlerts,
  });

export const useEWSScan = () =>
  useMutation({
    mutationFn: (limit?: number) => muleApi.triggerEWSScan(limit),
  });

export const useContamination = (accountId: string) =>
  useQuery({
    queryKey: ['mule', 'contamination', accountId],
    queryFn: () => muleApi.getContamination(accountId),
    enabled: !!accountId,
  });

export const useTrainModels = () =>
  useMutation({
    mutationFn: muleApi.trainModels,
  });

export const useTrainingStatus = (refetchInterval?: number | false) =>
  useQuery({
    queryKey: ['mule', 'models', 'status'],
    queryFn: muleApi.getTrainingStatus,
    refetchInterval,
  });

// ── Cross-Channel ──
export const useChannelProfile = (accountId: string) =>
  useQuery({
    queryKey: ['cross-channel', 'profile', accountId],
    queryFn: () => crossChannelApi.getProfile(accountId),
    enabled: !!accountId,
  });

export const useChannelHopAlerts = () =>
  useQuery({
    queryKey: ['cross-channel', 'hop-alerts'],
    queryFn: crossChannelApi.getHopAlerts,
  });

export const useChannelStats = () =>
  useQuery({
    queryKey: ['cross-channel', 'channel-stats'],
    queryFn: crossChannelApi.getChannelStats,
    refetchInterval: 10000,
  });

export const useInterBankFeed = () =>
  useQuery({
    queryKey: ['cross-channel', 'inter-bank'],
    queryFn: crossChannelApi.getInterBank,
  });

export const useUnifiedRiskScore = (accountId: string) =>
  useQuery({
    queryKey: ['cross-channel', 'unified-score', accountId],
    queryFn: () => crossChannelApi.getUnifiedScore(accountId),
    enabled: !!accountId,
  });

export const useCrossChannelSimulate = () =>
  useMutation({
    mutationFn: crossChannelApi.simulateFeed,
  });

// ── eCourts India Integration ──
export const useSearchECourts = () => {
  return useMutation({
    mutationFn: (query: string) => alertsApi.searchECourts(query),
  });
};

export const useECourtsCase = (cnr: string) => {
  return useQuery({
    queryKey: ['ecourts', 'case', cnr],
    queryFn: () => alertsApi.getECourtsCase(cnr),
    enabled: !!cnr,
  });
};

export const useTrackECourtsCase = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cnr, accountId }: { cnr: string; accountId?: string }) =>
      alertsApi.trackECourtsCase(cnr, accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] });
    },
  });
};
