import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Database,
  MapPin,
  Play,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { accountsApi } from '@/lib/api';
import {
  useGovDataRefresh,
  useGovDataStatus,
  useGovFraudContext,
  useGovGeoRisk,
  useGovUpiBaseline,
} from '@/hooks/useApi';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { fadeInUp, staggerContainer } from '@/lib/animations';
import type { GovGeoRiskRow } from '@/types/api';

const resources = [
  { key: 'upi', label: 'UPI Stats', id: 'a40ccebb' },
  { key: 'rupay', label: 'RuPay Cards', id: '5c3d7a42' },
  { key: 'frauds', label: 'RBI Frauds', id: '3d50bf0b' },
  { key: 'cybercrime', label: 'Cybercrime', id: '5116f39e' },
  { key: 'npci', label: 'NPCI Stats', id: '46b72197' },
];

function healthFor(minutes?: number | null) {
  if (minutes == null) return { label: 'ERROR', text: 'text-red-400', dot: 'bg-red-500', symbol: '✕' };
  if (minutes < 360) return { label: 'LIVE', text: 'text-green-400', dot: 'bg-green-500', symbol: '●' };
  if (minutes <= 1440) return { label: 'STALE', text: 'text-amber-400', dot: 'bg-amber-500', symbol: '○' };
  return { label: 'ERROR', text: 'text-red-400', dot: 'bg-red-500', symbol: '✕' };
}

function formatNumber(value?: number, digits = 0) {
  return Number(value || 0).toLocaleString('en-IN', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200 ${className}`} />;
}

function RealBadge() {
  return <Badge variant="green" size="sm" pulse>● REAL DATA</Badge>;
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
        {icon}
        {title}
      </h2>
      <RealBadge />
    </div>
  );
}

function ErrorNotice() {
  return (
    <div className="mb-4 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
      Feed Offline — Showing Cached Data
    </div>
  );
}

function accountCountKey(row: GovGeoRiskRow) {
  return row.state.toLowerCase().replace(/\s+/g, '_');
}

export default function GovDataIntelligence() {
  const [toast, setToast] = useState('');
  const [demoPulse, setDemoPulse] = useState(false);
  const rbiSectionRef = useRef<HTMLDivElement | null>(null);

  const status = useGovDataStatus();
  const upi = useGovUpiBaseline();
  const fraud = useGovFraudContext();
  const geo = useGovGeoRisk();
  const refresh = useGovDataRefresh();

  const topStates = useMemo(() => (geo.data?.rankings || []).slice(0, 12), [geo.data]);
  const accountCounts = useQuery({
    queryKey: ['govdata', 'state-account-counts', topStates.map(accountCountKey).join('|')],
    enabled: topStates.length > 0,
    queryFn: async () => {
      const pairs = await Promise.all(
        topStates.map(async (row) => {
          const accounts = await accountsApi.getAll({ state: row.state, limit: 1000 });
          return [row.state, accounts.length] as const;
        })
      );
      return Object.fromEntries(pairs) as Record<string, number>;
    },
  });

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 4500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const allLoading = status.isLoading || upi.isLoading || fraud.isLoading || geo.isLoading;
  const anyError = status.isError || upi.isError || fraud.isError || geo.isError;
  const freshest = Math.min(
    ...Object.values(status.data?.freshness_minutes || {}).filter((value): value is number => value !== null)
  );
  const lastRefreshed = Number.isFinite(freshest) ? `${formatNumber(freshest, 0)} mins ago` : 'Never';

  const upiSeries = upi.data?.series || [];
  const monthlyAvg = upi.data?.monthly_avg_mn_transactions || 0;
  const chartThreshold = monthlyAvg * 3.5;
  const peak = upiSeries.reduce((best, item) => (
    item.volume_mn_transactions > (best?.volume_mn_transactions || 0) ? item : best
  ), upiSeries[0]);

  const fraudRows = fraud.data?.records || [];
  const maxCases = Math.max(...fraudRows.map((row) => row.num_cases || 0), 1);

  const refreshAll = async (demo = false) => {
    await refresh.mutateAsync();
    if (demo) {
      setDemoPulse(true);
      setToast('✓ Real government data ingested — 5 feeds updated from data.gov.in');
      window.setTimeout(() => {
        rbiSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 650);
      window.setTimeout(() => setDemoPulse(false), 3600);
    }
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6 rounded-2xl bg-slate-50 p-4 text-slate-900">
      <motion.div variants={fadeInUp} className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="flex items-center gap-3 text-3xl font-extrabold tracking-tight">
            <ShieldCheck size={28} className="text-emerald-600" />
            Live Government Intelligence
          </h1>
          <p className="mt-1 text-sm text-slate-600">Real data.gov.in feeds wired into SQLite, Kafka, STR enrichment, and risk scoring.</p>
        </div>
        <Button
          size="md"
          icon={<Play size={16} />}
          loading={refresh.isPending}
          onClick={() => refreshAll(true)}
          className="bg-emerald-600 text-white hover:bg-emerald-500"
        >
          Run Live Demo Sequence
        </Button>
      </motion.div>

      {toast && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed right-6 top-24 z-[60] rounded-lg border border-emerald-200 bg-white px-4 py-3 text-sm font-semibold text-emerald-700 shadow-xl shadow-slate-200"
        >
          {toast}
        </motion.div>
      )}

      <motion.section variants={fadeInUp} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {allLoading ? resources.map((resource) => <Skeleton key={resource.key} className="h-10" />) : resources.map((resource) => {
              const health = healthFor(status.data?.freshness_minutes?.[resource.key]);
              return (
                <div key={resource.key} className="flex items-center justify-between rounded-full border border-slate-200 bg-slate-50 px-3 py-2 shadow-sm">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-slate-800">{resource.label} <span className="text-slate-500">[{resource.id}]</span></p>
                  </div>
                  <span className={`ml-2 flex items-center gap-1.5 text-[10px] font-bold ${health.text}`}>
                    <span className={`h-2 w-2 rounded-full ${health.dot}`} />
                    {health.symbol} {health.label}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
            <span className="text-xs text-slate-600">Last Refreshed: <span className="font-semibold text-slate-900">{lastRefreshed}</span></span>
            <Button
              size="sm"
              variant="secondary"
              icon={<RefreshCw size={14} />}
              loading={refresh.isPending}
              className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              onClick={() => refreshAll(false)}
            >
              Refresh All
            </Button>
          </div>
        </div>
      </motion.section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <motion.section variants={fadeInUp} className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:col-span-7 ${demoPulse ? 'animate-pulse ring-2 ring-red-400' : ''}`}>
          <SectionHeader icon={<Activity size={16} className="text-cyan-600" />} title="National UPI Transaction Baseline (data.gov.in • Real)" />
          {upi.isError && <ErrorNotice />}
          {upi.isLoading ? (
            <Skeleton className="h-[320px]" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={upiSeries} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="upiVelocity" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a' }}
                  formatter={(value, name) => [formatNumber(Number(value), 2), name === 'volume_mn_transactions' ? 'Volume (Mn)' : name]}
                  labelFormatter={(label, payload) => {
                    const row = payload?.[0]?.payload;
                    return `${label} • Value ₹${formatNumber(row?.value_cr_rupees, 2)} Cr • MoM ${formatNumber(row?.mom_change_pct, 2)}%`;
                  }}
                />
                <ReferenceLine
                  y={chartThreshold}
                  stroke="#ef4444"
                  strokeDasharray="6 6"
                  label={{ value: 'Anomaly Threshold = 3.5× monthly avg', fill: '#b91c1c', fontSize: 10, position: 'insideTopRight' }}
                />
                <Area type="monotone" dataKey="volume_mn_transactions" stroke="#22d3ee" strokeWidth={2} fill="url(#upiVelocity)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-600">Current Monthly Avg Volume</p>
              <p className="mt-1 text-xl font-bold text-cyan-700">{formatNumber(monthlyAvg, 2)} Mn</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-600">Peak Month</p>
              <p className="mt-1 text-xl font-bold text-slate-900">{peak?.month || '—'}</p>
              <p className="text-xs text-slate-600">{formatNumber(peak?.volume_mn_transactions, 2)} Mn</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs text-slate-600">Anomaly Threshold</p>
              <p className="mt-1 text-xl font-bold text-red-700">{formatNumber(upi.data?.velocity_spike_threshold_mn_transactions, 2)}</p>
              <p className="text-xs text-slate-600">txns/day per account baseline</p>
            </div>
          </div>
        </motion.section>

        <motion.section ref={rbiSectionRef} variants={fadeInUp} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:col-span-5">
          <SectionHeader icon={<BarChart3 size={16} className="text-red-600" />} title="Official RBI Fraud Registry (data.gov.in • Real)" />
          {fraud.isError && <ErrorNotice />}
          <div className="mb-3 flex justify-end">
            <Badge variant="green" size="sm">Powers STR Enrichment ✓</Badge>
          </div>
          {fraud.isLoading ? (
            <Skeleton className="h-[230px]" />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={fraudRows}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis dataKey="fraud_category" tick={{ fill: '#475569', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: 8, color: '#0f172a' }} />
                <Bar dataKey="num_cases" radius={[4, 4, 0, 0]}>
                  {fraudRows.map((row) => {
                    const category = row.fraud_category.toLowerCase();
                    const color = category.includes('card') || category.includes('internet') || category.includes('upi') ? '#ef4444' : category.includes('loan') ? '#f97316' : '#9ca3af';
                    return <Cell key={`${row.year}-${row.fraud_category}`} fill={color} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600">
                <tr>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Cases (Year)</th>
                  <th className="px-3 py-2">Avg Amount ₹</th>
                  <th className="px-3 py-2">Risk Weight</th>
                </tr>
              </thead>
              <tbody>
                {fraudRows.map((row) => (
                  <tr key={`${row.year}-${row.fraud_category}`} className="border-t border-slate-200 bg-white">
                    <td className="px-3 py-2 font-semibold text-slate-900">{row.fraud_category}</td>
                    <td className="px-3 py-2 text-slate-700">{formatNumber(row.num_cases)} ({row.year})</td>
                    <td className="px-3 py-2 text-slate-700">{formatNumber(row.amount_lakh * 100000, 0)}</td>
                    <td className="px-3 py-2 font-semibold text-red-700">{formatNumber((row.num_cases / maxCases) * 100, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>
      </div>

      <motion.section variants={fadeInUp} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <SectionHeader icon={<MapPin size={16} className="text-amber-600" />} title="State-wise Cybercrime Hotspots (NCRP Data • data.gov.in • Real)" />
        {geo.isError && <ErrorNotice />}
        {geo.isLoading ? (
          <Skeleton className="h-[360px]" />
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase tracking-wider text-slate-600">
                <tr>
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">State</th>
                  <th className="px-4 py-3">Cases</th>
                  <th className="px-4 py-3">Risk Delta</th>
                  <th className="px-4 py-3">Account Count in DB</th>
                </tr>
              </thead>
              <tbody>
                {topStates.map((row) => {
                  const rowClass = row.rank <= 5 ? 'bg-red-50 text-red-950' : row.rank <= 10 ? 'bg-amber-50 text-amber-950' : 'bg-white text-slate-900';
                  return (
                    <tr key={row.state} className={`border-t border-slate-200 ${rowClass}`}>
                      <td className="px-4 py-3 font-bold">#{row.rank}</td>
                      <td className="px-4 py-3 font-semibold">{row.state}</td>
                      <td className="px-4 py-3">{formatNumber(row.total_cases)}</td>
                      <td className="px-4 py-3">{row.rank <= 5 ? '+0.08 to risk score' : '+0.00'}</td>
                      <td className="px-4 py-3">
                        {accountCounts.isLoading ? <span className="text-slate-500">Loading…</span> : formatNumber(accountCounts.data?.[row.state] || 0)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </motion.section>

      {anyError && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle size={16} className="mr-2 inline" />
          One or more live feeds are offline. Cached data remains visible where available.
        </div>
      )}

      <div className="hidden">
        <Database />
        <CheckCircle2 />
      </div>
    </motion.div>
  );
}
