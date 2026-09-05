import { motion } from 'framer-motion';
import { Scale, FileText, AlertTriangle, Shield, Newspaper } from 'lucide-react';
import { useWatchlist, useSTRs, useRFA, useRegulatoryNews, useFileSTR } from '@/hooks/useApi';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import GovDataIntelligence from './GovDataIntelligence';

function Win98Window({ title, icon: Icon, children, className = '' }: { title: string; icon: any; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`}>
      <div className="border-b border-slate-200 bg-slate-50 px-3 py-2 flex items-center gap-2">
        <Icon size={14} className="text-blue-600" />
        <span className="text-xs font-bold text-slate-800 flex-1">{title}</span>
        <div className="flex gap-0.5">
          {['_', '□', '×'].map(c => (
            <button key={c} className="w-4 h-3.5 rounded border border-slate-300 bg-white text-[8px] font-bold text-slate-600 flex items-center justify-center">{c}</button>
          ))}
        </div>
      </div>
      <div className="p-2">{children}</div>
    </div>
  );
}

export default function RegulatoryPage() {
  const { data: watchlistData } = useWatchlist();
  const { data: strs } = useSTRs();
  const { data: rfa } = useRFA();
  const { data: news } = useRegulatoryNews();
  const fileSTR = useFileSTR();

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-4 rounded-2xl bg-slate-50 p-4 text-slate-900">
      <motion.div variants={fadeInUp} className="flex items-center gap-3">
        <Scale size={20} className="text-blue-600" />
        <h1 className="text-2xl font-bold text-slate-950">Regulatory Compliance Workstation</h1>
      </motion.div>

      <GovDataIntelligence />

      <motion.div variants={fadeInUp} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* CRILC / Watchlist */}
        <Win98Window title="🏛 CRILC WATCHLIST MONITOR" icon={Shield}>
          <div className="bg-white max-h-[280px] overflow-y-auto border border-inset">
            {!watchlistData?.watchlist?.length ? (
              <p className="p-2 text-xs text-gray-500">No watchlist entries</p>
            ) : watchlistData.watchlist.map((w) => (
              <div key={w.account_id} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100">
                <div className="flex justify-between">
                  <span className="font-bold text-red-800">{w.name}</span>
                  <span className="bg-red-100 text-red-700 px-1 rounded text-[10px]">{w.risk_profile}</span>
                </div>
                <div className="text-gray-600">{w.account_id} | {w.city}</div>
                <div className="text-gray-500 mt-0.5 italic">{w.reason}</div>
              </div>
            ))}
          </div>
        </Win98Window>

        {/* STR Queue */}
        <Win98Window title="📝 STR FILING QUEUE — FIU-IND" icon={FileText}>
          <div className="bg-white max-h-[280px] overflow-y-auto border border-inset">
            {!strs?.length ? (
              <p className="p-2 text-xs text-gray-500">No pending STRs</p>
            ) : strs.map((s) => (
              <div key={s.str_id} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100">
                <div className="flex justify-between items-center">
                  <span className="font-bold">{s.str_id}</span>
                  <button
                    onClick={() => fileSTR.mutate({ strId: s.str_id })}
                    className="bg-[#000080] text-white px-2 py-0.5 text-[10px] border border-t-[#dfdfdf] border-l-[#dfdfdf] border-b-[#404040] border-r-[#404040]"
                  >
                    FILE TO FIU
                  </button>
                </div>
                <div className="text-gray-600">{s.fraud_type} | ₹{s.amount?.toLocaleString()}</div>
              </div>
            ))}
          </div>
        </Win98Window>

        {/* RFA */}
        <Win98Window title="🚩 RED FLAGGED ACCOUNTS" icon={AlertTriangle}>
          <div className="bg-white max-h-[280px] overflow-y-auto border border-inset">
            {!rfa?.rfa_accounts?.length ? (
              <p className="p-2 text-xs text-gray-500">No RFA entries</p>
            ) : rfa.rfa_accounts.map((r) => (
              <div key={r.account_id} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100">
                <div className="flex justify-between">
                  <span className="font-bold text-red-800">{r.name}</span>
                  <span className="text-gray-500">{r.classification || 'PENDING'}</span>
                </div>
                <div className="text-gray-600">{r.reason}</div>
                <div className="text-gray-400 mt-0.5">CRILC deadline: {r.crilc_report_deadline}</div>
              </div>
            ))}
          </div>
          {rfa && (
            <div className="bg-yellow-100 border border-yellow-400 p-1 mt-1 text-[10px] text-yellow-800">
              ⚠ {rfa.overdue_crilc_count} overdue CRILC | {rfa.pending_classifications_count} pending classifications
            </div>
          )}
        </Win98Window>

        {/* News */}
        <Win98Window title="📰 REGULATORY NEWS FEED" icon={Newspaper}>
          <div className="bg-white max-h-[280px] overflow-y-auto border border-inset">
            {!news?.length ? (
              <p className="p-2 text-xs text-gray-500">No regulatory news</p>
            ) : news.slice(0, 10).map((n, i) => (
              <div key={i} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100">
                <a href={n.link} target="_blank" rel="noopener noreferrer" className="font-bold text-blue-800 hover:underline">{n.title}</a>
                <div className="flex justify-between text-gray-500 mt-0.5">
                  <span>{n.source}</span>
                  <span className={`font-bold ${n.risk_score > 0.7 ? 'text-red-600' : 'text-gray-500'}`}>
                    Risk: {(n.risk_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Win98Window>
      </motion.div>
    </motion.div>
  );
}
