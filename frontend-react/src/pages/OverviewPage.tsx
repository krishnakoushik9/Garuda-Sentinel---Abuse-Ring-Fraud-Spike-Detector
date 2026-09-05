import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Shield, Users, ArrowRightLeft, AlertTriangle, Activity, GitBranch, 
  AlertCircle, Flame
} from 'lucide-react';
import { StatCard } from '@/components/ui/StatCard';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useSystemStore } from '@/stores/systemStore';
import { useGovDataStatus, useGovFraudContext, useGovUpiBaseline } from '@/hooks/useApi';

// Mock time-series data for risk trend
const riskTrend = Array.from({ length: 24 }, (_, i) => ({
  hour: `${i}:00`,
  risk: Math.random() * 0.3 + 0.4,
  volume: Math.floor(Math.random() * 500 + 200),
}));

export default function OverviewPage() {
  // Connect system Zustand store
  const {
    dataSource,
    cobolStatus,
    realTimeMetrics,
    fetchDataSourceStatus,
    fetchCobolStatus,
    fetchRealTimeMetrics
  } = useSystemStore();
  const { data: govStatus } = useGovDataStatus();
  const { data: govUpi } = useGovUpiBaseline();
  const { data: govFraud } = useGovFraudContext();

  // Sync / Poll metrics
  useEffect(() => {
    fetchDataSourceStatus();
    fetchCobolStatus();
    fetchRealTimeMetrics();

    // Fast polling for system metrics & engine status
    const interval = setInterval(() => {
      fetchRealTimeMetrics();
      fetchCobolStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      
      {/* Page Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between border-b border-white/[0.08] pb-5">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Intelligence Command Center
            <span className="text-xs font-mono py-1 px-2 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              FDS V5.0
            </span>
          </h1>
          <p className="text-sm text-white/40 mt-1">Real-time fraud operations room & hybrid COBOL simulation control</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={dataSource === 'COBOL_SYNTHETIC' ? 'green' : 'cyan'} pulse>
            SOURCE: {dataSource.replace('_', ' ')}
          </Badge>
          <Badge variant={cobolStatus.running ? 'green' : 'amber'} pulse={cobolStatus.running}>
            SIMULATOR: {cobolStatus.status.toUpperCase()}
          </Badge>
        </div>
      </motion.div>

      {/* Main Container: Stretches cleanly across full widescreen width */}
      <div className="space-y-6">
        
        {/* Real-time System Metrics Health Grid */}
        <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Accounts" value={realTimeMetrics.accounts} icon={<Users size={18} />} variant="cyan" />
          <StatCard label="Total Transactions" value={realTimeMetrics.transactions} icon={<ArrowRightLeft size={18} />} variant="purple" />
          <StatCard label="High Risk Alerts" value={realTimeMetrics.alerts} icon={<AlertTriangle size={18} />} variant="red" />
          <StatCard label="Mule Suspects" value={realTimeMetrics.mules} icon={<Shield size={18} />} variant="amber" />
        </motion.div>

        {govStatus?.use_real_govdata && (
          <motion.div variants={fadeInUp} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-lg border border-green-500/25 bg-green-500/10 p-4">
              <p className="text-xs uppercase tracking-wider text-green-300">Government Feeds</p>
              <p className="mt-1 text-xl font-bold text-white">5 Gov Feeds Active</p>
            </div>
            <div className="rounded-lg border border-cyan-500/25 bg-cyan-500/10 p-4">
              <p className="text-xs uppercase tracking-wider text-cyan-300">UPI Baseline</p>
              <p className="mt-1 text-xl font-bold text-white">{(govUpi?.monthly_avg_mn_transactions || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })} Mn txns/mo</p>
            </div>
            <div className="rounded-lg border border-red-500/25 bg-red-500/10 p-4">
              <p className="text-xs uppercase tracking-wider text-red-300">RBI Fraud Registry</p>
              <p className="mt-1 text-xl font-bold text-white">{(govFraud?.records || []).reduce((sum, row) => sum + (row.num_cases || 0), 0).toLocaleString('en-IN')} cases tracked</p>
            </div>
          </motion.div>
        )}

        {/* Core Visualizations Row */}
        <motion.div variants={fadeInUp} className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          
          {/* Risk Trend Visualizer (Expanded to 8/12 columns) */}
          <GlassCard padding="lg" className="xl:col-span-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-semibold text-white/70 uppercase tracking-wider flex items-center gap-2">
                <Activity size={14} className="text-cyan-400" />
                Real-time Risk Trend (24h)
              </h3>
              <span className="text-[10px] text-white/30 font-mono">UPDATES EVERY 5S</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={riskTrend}>
                <defs>
                  <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#00f0ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="hour" tick={{ fill: '#666', fontSize: 9 }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fill: '#666', fontSize: 9 }} axisLine={false} tickLine={false} domain={[0, 1]} />
                <Tooltip contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: 8, fontSize: 11 }} />
                <Area type="monotone" dataKey="risk" stroke="#00f0ff" strokeWidth={2} fill="url(#riskGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </GlassCard>

          {/* Network Intelligence Nodes info (Expanded to 4/12 columns) */}
          <GlassCard padding="lg" className="xl:col-span-4 flex flex-col justify-between">
            <div className="h-full flex flex-col justify-between">
              <h3 className="text-xs font-semibold text-white/70 uppercase tracking-wider flex items-center gap-2 mb-4">
                <GitBranch size={14} className="text-purple-400" />
                Graph Neighborhood
              </h3>
              <div className="space-y-4 my-auto">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex justify-between items-center hover:bg-white/[0.04] transition-all">
                  <span className="text-xs text-white/50">Graph Nodes</span>
                  <span className="text-base font-bold text-cyan-400">{realTimeMetrics.nodes.toLocaleString()}</span>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex justify-between items-center hover:bg-white/[0.04] transition-all">
                  <span className="text-xs text-white/50">Graph Edges</span>
                  <span className="text-base font-bold text-purple-400">{realTimeMetrics.edges.toLocaleString()}</span>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex justify-between items-center hover:bg-white/[0.04] transition-all">
                  <span className="text-xs text-white/50">EWS Alerts</span>
                  <span className="text-base font-bold text-red-400">{realTimeMetrics.ewsEvents.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </GlassCard>
        </motion.div>

        {/* Threat Intelligence / Realtime Alert Stream */}
        <motion.div variants={fadeInUp} className="w-full">
          <GlassCard padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-semibold text-white/70 uppercase tracking-wider flex items-center gap-2">
                <Flame size={14} className="text-red-400" />
                Global Threat Feed (Simulated Round Logs)
              </h3>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
              {realTimeMetrics.alerts > 0 ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <div key={idx} className="flex justify-between items-center p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                    <div className="flex items-center gap-3">
                      <AlertCircle size={18} className="text-red-500" />
                      <div>
                        <p className="text-xs text-white font-mono font-bold">STRUCTURING_BREACH_ALERT_{100 + idx}</p>
                        <p className="text-[10px] text-white/30">Mule Candidate suspected in community {2 + idx}</p>
                      </div>
                    </div>
                    <Badge variant="red" size="sm">CRITICAL</Badge>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-white/30 text-xs font-mono">
                  No critical threat events detected. Simulator is running on standby.
                </div>
              )}
            </div>
          </GlassCard>
        </motion.div>

      </div>

    </motion.div>
  );
}
