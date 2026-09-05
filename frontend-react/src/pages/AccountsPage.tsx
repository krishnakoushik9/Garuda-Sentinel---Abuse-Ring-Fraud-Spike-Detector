import { motion } from 'framer-motion';
import { Users, Search } from 'lucide-react';
import { useState } from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { useAccounts } from '@/hooks/useApi';
import { staggerContainer, fadeInUp } from '@/lib/animations';

export default function AccountsPage() {
  const [page, setPage] = useState(1);
  const { data: accounts, isLoading } = useAccounts({ page, limit: 20 });

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      <motion.div variants={fadeInUp}>
        <h1 className="text-2xl font-bold text-white">Account Intelligence</h1>
        <p className="text-sm text-white/40 mt-1">Risk profiling, community clustering & account scoring</p>
      </motion.div>

      <motion.div variants={fadeInUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <GlassCard key={i} padding="md" className="animate-pulse h-40" />
          ))
        ) : accounts?.map((acc) => (
          <GlassCard key={acc.account_id} padding="md" hover>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
                  <Users size={18} className="text-white/50" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{acc.name}</p>
                  <p className="text-xs text-white/40 font-mono">{acc.account_id}</p>
                </div>
              </div>
              <Badge variant={acc.risk_profile === 'HIGH' || acc.risk_profile === 'CRITICAL' ? 'red' : acc.risk_profile === 'MEDIUM' ? 'amber' : 'green'} size="sm">
                {acc.risk_profile}
              </Badge>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-4">
              <div className="text-center p-2 rounded bg-white/[0.02]">
                <p className="text-xs text-white/40">Balance</p>
                <p className="text-sm font-bold text-white">₹{acc.balance?.toLocaleString()}</p>
              </div>
              <div className="text-center p-2 rounded bg-white/[0.02]">
                <p className="text-xs text-white/40">PageRank</p>
                <p className="text-sm font-bold text-cyan-400">{acc.pagerank?.toFixed(4)}</p>
              </div>
              <div className="text-center p-2 rounded bg-white/[0.02]">
                <p className="text-xs text-white/40">Community</p>
                <p className="text-sm font-bold text-purple-400">{acc.community_id ?? '—'}</p>
              </div>
            </div>
          </GlassCard>
        ))}
      </motion.div>

      <div className="flex justify-center gap-2">
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} className="px-4 py-2 text-sm text-white/50 hover:text-white disabled:opacity-30">← Previous</button>
        <span className="px-4 py-2 text-sm text-white/40">Page {page}</span>
        <button onClick={() => setPage(page + 1)} className="px-4 py-2 text-sm text-white/50 hover:text-white">Next →</button>
      </div>
    </motion.div>
  );
}
