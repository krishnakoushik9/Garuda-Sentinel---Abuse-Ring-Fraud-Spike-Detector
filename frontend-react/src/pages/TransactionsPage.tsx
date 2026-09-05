import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, ArrowRightLeft } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useTransactions, useTransactionStats } from '@/hooks/useApi';
import { StatCard } from '@/components/ui/StatCard';
import { staggerContainer, fadeInUp } from '@/lib/animations';

const tabs = ['All Transactions', 'Intercepted', 'Suspicious', 'Flagged Accounts'] as const;
type Tab = typeof tabs[number];

const riskTierMap: Record<Tab, string | undefined> = {
  'All Transactions': undefined,
  'Intercepted': 'high',
  'Suspicious': 'suspicious',
  'Flagged Accounts': 'mule',
};

export default function TransactionsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('All Transactions');
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  const { data: transactions, isLoading } = useTransactions({
    page,
    limit: 50,
    risk_tier: riskTierMap[activeTab] ?? 'all',
    search: searchTerm || undefined,
  });
  const { data: stats } = useTransactionStats();

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      <motion.div variants={fadeInUp}>
        <h1 className="text-2xl font-bold text-white">Transaction Intelligence</h1>
        <p className="text-sm text-white/40 mt-1">Monitor and analyze all banking transactions</p>
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Transactions" value={stats?.total_count ?? 0} icon={<ArrowRightLeft size={18} />} variant="cyan" />
        <StatCard label="Fraud Events" value={stats?.fraud_count ?? 0} variant="red" />
        <StatCard label="Mule Suspects" value={stats?.mule_count ?? 0} variant="amber" />
        <StatCard label="Avg Risk Score" value={(stats?.avg_risk_score ?? 0) * 100} suffix="%" variant="purple" format="percent" />
      </motion.div>

      {/* Tabs + Search */}
      <motion.div variants={fadeInUp} className="flex flex-col md:flex-row justify-between gap-4">
        <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setPage(1); }}
              className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                activeTab === tab
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                  : 'text-white/50 hover:text-white/70 border border-transparent'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
          <input
            type="text"
            placeholder="Search transactions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06] text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/40 w-full md:w-64"
          />
        </div>
      </motion.div>

      {/* Table */}
      <motion.div variants={fadeInUp}>
        <GlassCard padding="none">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Transaction ID', 'Sender', 'Receiver', 'Amount', 'Channel', 'Risk', 'Status', 'Time'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-white/40 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={8} className="text-center py-12 text-white/30">Loading...</td></tr>
                ) : !transactions?.length ? (
                  <tr><td colSpan={8} className="text-center py-12 text-white/30">No transactions found</td></tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.transaction_id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-cyan-400">{tx.transaction_id}</td>
                      <td className="px-4 py-3 text-xs text-white/70">{tx.sender_account}</td>
                      <td className="px-4 py-3 text-xs text-white/70">{tx.receiver_account}</td>
                      <td className="px-4 py-3 text-xs text-white font-medium">₹{tx.amount.toLocaleString()}</td>
                      <td className="px-4 py-3"><Badge variant="neutral" size="sm">{tx.channel}</Badge></td>
                      <td className="px-4 py-3">
                        <Badge variant={tx.risk_score > 0.7 ? 'red' : tx.risk_score > 0.4 ? 'amber' : 'green'} size="sm">
                          {(tx.risk_score * 100).toFixed(0)}%
                        </Badge>
                      </td>
                      <td className="px-4 py-3"><Badge variant={tx.status === 'BLOCKED' ? 'red' : 'green'} size="sm">{tx.status}</Badge></td>
                      <td className="px-4 py-3 text-xs text-white/40">{new Date(tx.timestamp).toLocaleTimeString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-white/[0.06]">
            <span className="text-xs text-white/40">Page {page}</span>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}>Previous</Button>
              <Button variant="ghost" size="sm" onClick={() => setPage(page + 1)} disabled={!transactions?.length || transactions.length < 50}>Next</Button>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    </motion.div>
  );
}
