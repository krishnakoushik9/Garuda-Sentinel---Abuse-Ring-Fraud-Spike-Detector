import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, Loader2, Cpu, FileText, AlertTriangle, ShieldCheck, 
  Terminal, ArrowRight, Play, CheckCircle2, RefreshCw
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useInvestigations, useStartInvestigation } from '@/hooks/useApi';
import { staggerContainer, fadeInUp } from '@/lib/animations';

interface UIState {
  title: string;
  badge: string;
  severity: 'success' | 'warning' | 'danger' | 'info';
  color: string;
  cardBg: string;
  innerBg: string;
  titleColor: string;
  descColor: string;
  badgeBg: string;
  alertBg: string;
  latencyColor: string;
  description: string;
  icon: any;
}

const getDecisionUIState = (decision: string): UIState => {
  const norm = (decision || '').toUpperCase().trim();
  switch (norm) {
    case 'ALLOW':
      return {
        title: "TRANSACTION APPROVED",
        badge: "ALLOW",
        severity: "success",
        color: "green",
        cardBg: "bg-emerald-50 border-2 border-emerald-500/30",
        innerBg: "bg-white border border-emerald-200/50",
        titleColor: "text-emerald-800",
        descColor: "text-emerald-700/80",
        badgeBg: "bg-emerald-600",
        alertBg: "bg-emerald-100/50 text-emerald-800 border border-emerald-200/30",
        latencyColor: "text-emerald-600",
        description: "Core Banking Sentinel (CBSA) successfully approved transaction after ledger audit validation.",
        icon: ShieldCheck,
      };
    case 'HOLD':
      return {
        title: "TRANSACTION HELD",
        badge: "HOLD",
        severity: "warning",
        color: "amber",
        cardBg: "bg-amber-50 border-2 border-amber-500/30",
        innerBg: "bg-white border border-amber-200/50",
        titleColor: "text-amber-800",
        descColor: "text-amber-700/80",
        badgeBg: "bg-amber-600",
        alertBg: "bg-amber-100/50 text-amber-800 border border-amber-200/30",
        latencyColor: "text-amber-600",
        description: "Core Banking Sentinel (CBSA) successfully intercepted transfer before clearing cycle completed.",
        icon: AlertTriangle,
      };
    case 'FREEZE':
      return {
        title: "TRANSACTION FROZEN",
        badge: "FREEZE",
        severity: "danger",
        color: "red",
        cardBg: "bg-red-50 border-2 border-red-500/30",
        innerBg: "bg-white border border-red-200/50",
        titleColor: "text-red-800",
        descColor: "text-red-700/80",
        badgeBg: "bg-red-600",
        alertBg: "bg-red-100/50 text-red-800 border border-red-200/30",
        latencyColor: "text-red-600",
        description: "Core Banking Sentinel (CBSA) successfully intercepted transfer before clearing cycle completed.",
        icon: AlertTriangle,
      };
    case 'ESCALATE':
    default:
      return {
        title: "ESCALATED FOR REVIEW",
        badge: "ESCALATE",
        severity: "info",
        color: "blue",
        cardBg: "bg-blue-50 border-2 border-blue-500/30",
        innerBg: "bg-white border border-blue-200/50",
        titleColor: "text-blue-800",
        descColor: "text-blue-700/85",
        badgeBg: "bg-blue-600",
        alertBg: "bg-blue-100/50 text-blue-800 border border-blue-200/30",
        latencyColor: "text-blue-600",
        description: "Transaction flagged and escalated for manual compliance audit.",
        icon: RefreshCw,
      };
  }
};

export default function InvestigatePage() {
  const { data: investigations, isLoading, refetch } = useInvestigations();
  const startMutation = useStartInvestigation();
  
  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'cobol' | 'forensic'>('cobol');

  // Forensic input states
  const [txnId, setTxnId] = useState('');
  const [accountId, setAccountId] = useState('');

  // COBOL Sentinel Simulator states
  const [ticketText, setTicketText] = useState(
    "URGENT COMPLAINT // National Cyber Crime Portal Ticket #NCCP-2026-8291.\n" +
    "Victim reported fraudulent transfer of ₹18,70,000 via UPI to gateway account IND-195.\n" +
    "Intelligence indicates immediate dispersal/laundering attempt to mule accounts IND-196 and IND-197 within next 60 minutes.\n" +
    "Target network: Mule Cluster JAI-619."
  );
  const [isSentinelRunning, setIsSentinelRunning] = useState(false);
  const [sentinelResult, setSentinelResult] = useState<any | null>(null);
  const [remainingQuota, setRemainingQuota] = useState<number | null>(null);
  const [sentinelLogs, setSentinelLogs] = useState<string[]>([]);

  const handleStartForensic = () => {
    if (txnId && accountId) {
      startMutation.mutate({ txnId, accountId });
      setTxnId('');
      setAccountId('');
    }
  };

  const handleRunSentinel = async () => {
    if (!ticketText.trim()) return;
    setIsSentinelRunning(true);
    setSentinelResult(null);
    setSentinelLogs([]);

    // Simulate mainframe booting logs
    const addLog = (msg: string, delay: number) => {
      return new Promise<void>((resolve) => {
        setTimeout(() => {
          setSentinelLogs(prev => [...prev, msg]);
          resolve();
        }, delay);
      });
    };

    await addLog("⚡ [COBOL] CBS TRANSACTION PATH INTERCEPTOR ACTIVE", 150);
    await addLog("📡 [COBOL] LISTENING ON ISO-8583 TRANSACTION TELEMETRY BUFFERS", 200);
    await addLog("🤖 [COBOL] COMPILING TICKET THROUGH SENTINEL KNOWLEDGE ENGINE", 300);
    await addLog("⚡ [COBOL] EXTRACTING SUSPECTED MULES & PROPAGATION TARGETS...", 300);

    try {
      const res = await fetch("/api/v1/cobol-sentinel/intercept", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ ticket_text: ticketText })
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      
      await addLog("🔒 [COBOL] MATCH FOUND AGAINST REGULATORY FRAUD FEED", 200);
      await addLog(`🔒 [COBOL] TARGET CLUSTER RESOLVED: ${data.cluster}`, 150);

      if (data.legal_logs && data.legal_logs.length > 0) {
        for (const log of data.legal_logs) {
          await addLog(log, 200);
        }
      }

      await addLog(`🔒 [COBOL] PREDICTED ESCAPE PROBABILITY: ${(data.risk_score * 100).toFixed(1)}%`, 150);
      await addLog(`🚫 [COBOL] SENTINEL ACTION ISSUED: ${data.action} TRANSACTION`, 100);

      setSentinelResult(data);
      setRemainingQuota(data.rate_limit_remaining);
    } catch (err: any) {
      await addLog(`❌ [COBOL] ENGINE FAULT: ${err.message || "Failed to contact Groq API"}`, 100);
    } finally {
      setIsSentinelRunning(false);
    }
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6 font-satoshi max-w-[1200px] mx-auto pb-12">
      <motion.div variants={fadeInUp} className="flex justify-between items-start flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-cabinet font-extrabold text-slate-900">Aegis Investigation Workstation</h1>
          <p className="text-sm text-slate-500 mt-1">Cross-layered core prevention and forensic deep analysis</p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-slate-100 p-1 border border-slate-200 rounded-xl">
          <button 
            onClick={() => setActiveTab('cobol')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'cobol' 
                ? 'bg-white text-slate-900 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Cpu size={14} />
            COBOL Core Sentinel
          </button>
          <button 
            onClick={() => setActiveTab('forensic')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'forensic' 
                ? 'bg-white text-slate-900 shadow-sm' 
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText size={14} />
            Forensic Analyst
          </button>
        </div>
      </motion.div>

      <AnimatePresence mode="wait">
        {activeTab === 'cobol' ? (
          <motion.div 
            key="cobol-sentinel"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-6"
          >
            {/* Left Column: Input Feed */}
            <div className="lg:col-span-7 space-y-6">
              <GlassCard padding="md" className="border-slate-200 bg-white">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-xs font-cabinet font-black text-slate-500 uppercase tracking-wider">Govt / Cybercrime Complaint Feed</h3>
                  {remainingQuota !== null && (
                    <Badge variant="purple" size="sm">Daily Quota: {remainingQuota}/45</Badge>
                  )}
                </div>
                
                <textarea 
                  value={ticketText}
                  onChange={(e) => setTicketText(e.target.value)}
                  placeholder="Paste Cybercrime Portal tickets, FIU feeds, or government warning alerts here..."
                  className="w-full min-h-[140px] p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/40 focus:ring-1 focus:ring-cyan-500/40 font-mono leading-relaxed"
                />

                <div className="flex gap-2 justify-end mt-4">
                  <Button 
                    variant="primary" 
                    onClick={handleRunSentinel}
                    loading={isSentinelRunning}
                    icon={<Play size={14} />}
                    className="bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-extrabold"
                  >
                    ⚡ Intercept & Parse Core Banking
                  </Button>
                </div>
              </GlassCard>

              {/* Terminal Logs Panel */}
              <GlassCard padding="md" className="bg-slate-950 border-slate-800 text-slate-200 min-h-[220px]">
                <div className="flex items-center gap-2 mb-3 border-b border-slate-800 pb-2">
                  <Terminal size={14} className="text-cyan-400" />
                  <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">Mainframe COBOL Interceptor Pipeline logs</span>
                </div>
                <div className="font-mono text-xs space-y-2 max-h-[220px] overflow-y-auto scrollbar-thin text-left">
                  {sentinelLogs.length === 0 ? (
                    <span className="text-slate-500">Awaiting Cybercrime ticket ingestion...</span>
                  ) : (
                    sentinelLogs.map((log, idx) => (
                      <div 
                        key={idx} 
                        className={
                          log.includes("❌") 
                            ? "text-red-400" 
                            : log.includes("[LEGAL]") 
                              ? "text-indigo-400 font-extrabold" 
                              : log.includes("🔒") || log.includes("🚫") 
                                ? "text-cyan-400 font-bold" 
                                : "text-slate-300"
                        }
                      >
                        {log}
                      </div>
                    ))
                  )}
                </div>
              </GlassCard>
            </div>

            {/* Right Column: Intercept Result */}
            <div className="lg:col-span-5">
              <AnimatePresence mode="wait">
                {sentinelResult ? (
                  <motion.div
                    key="sentinel-result"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="space-y-6"
                  >
                    {/* Big Intercept Card */}
                    {(() => {
                      const uiState = getDecisionUIState(sentinelResult.action);
                      const Icon = uiState.icon;
                      return (
                        <div className={`${uiState.cardBg} p-6 rounded-2xl shadow-xl space-y-4`}>
                          <div className="flex justify-between items-start">
                            <div className={`${uiState.badgeBg} text-white font-cabinet font-black text-[10px] uppercase px-2.5 py-1 rounded-md tracking-wider animate-pulse flex items-center gap-1`}>
                              <Icon size={10} />
                              {uiState.badge} PREVENTATIVE COMPLETED
                            </div>
                            <span className={`text-xs font-mono font-bold ${uiState.latencyColor}`}>LATENCY: 4.8ms</span>
                          </div>

                          <div className="text-left">
                            <h2 className={`text-xl font-cabinet font-black ${uiState.titleColor}`}>{uiState.title}</h2>
                            <p className={`text-xs ${uiState.descColor} mt-1 leading-relaxed`}>
                              {uiState.description}
                            </p>
                          </div>

                          <div className={`${uiState.innerBg} p-4 rounded-xl space-y-3.5 text-xs text-left`}>
                            <div className="flex justify-between border-b border-slate-100 pb-1.5">
                              <span className="text-slate-500 font-semibold">Victim Source:</span>
                              <span className="font-mono text-slate-800 font-extrabold">{sentinelResult.victim}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-100 pb-1.5">
                              <span className="text-slate-500 font-semibold">Mule Targets:</span>
                              <span className="font-mono text-indigo-700 font-extrabold">{sentinelResult.mules.join(', ')}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-100 pb-1.5">
                              <span className="text-slate-500 font-semibold">Intercepted Sum:</span>
                              <span className="font-mono text-slate-800 font-extrabold">₹{sentinelResult.amount.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between border-b border-slate-100 pb-1.5">
                              <span className="text-slate-500 font-semibold">Laundering Cluster:</span>
                              <span className="font-mono text-slate-850 font-extrabold">{sentinelResult.cluster}</span>
                            </div>
                            <div className="flex justify-between pt-1">
                              <span className="text-slate-500 font-semibold">Escape Probability:</span>
                              <span className={`font-bold ${uiState.latencyColor}`}>{(sentinelResult.risk_score * 100).toFixed(1)}%</span>
                            </div>

                            {sentinelResult.legal_intelligence && (
                              <>
                                <div className="border-t border-dashed border-slate-200 my-2 pt-2 text-center text-xs tracking-widest text-slate-400 font-bold select-none">
                                  ══════════════════
                                </div>
                                <div className="text-center font-cabinet font-black text-[10px] uppercase tracking-wider text-slate-500 mb-2">
                                  LEGAL INTELLIGENCE
                                </div>
                                <div className="flex justify-between border-b border-slate-100 pb-1.5">
                                  <span className="text-slate-500 font-semibold">Court Matches:</span>
                                  <span className="font-mono text-slate-800 font-extrabold">{sentinelResult.legal_intelligence.court_matches}</span>
                                </div>
                                <div className="flex justify-between border-b border-slate-100 pb-1.5">
                                  <span className="text-slate-500 font-semibold">Fraud Cases:</span>
                                  <span className="font-mono text-slate-800 font-extrabold">{sentinelResult.legal_intelligence.fraud_related_cases}</span>
                                </div>
                                <div className="flex justify-between border-b border-slate-100 pb-1.5">
                                  <span className="text-slate-500 font-semibold">Cybercrime Cases:</span>
                                  <span className="font-mono text-slate-800 font-extrabold">{sentinelResult.legal_intelligence.cybercrime_cases}</span>
                                </div>
                                <div className="flex justify-between pt-1">
                                  <span className="text-slate-500 font-semibold">Legal Risk:</span>
                                  <span className="font-mono text-indigo-600 font-black">{sentinelResult.legal_intelligence.legal_risk_score}%</span>
                                </div>
                                <div className="border-b border-dashed border-slate-200 my-2 pb-2 text-center text-xs tracking-widest text-slate-400 font-bold select-none">
                                  ══════════════════
                                </div>
                              </>
                            )}
                          </div>

                          {/* Explanation box */}
                          <p className={`text-xs ${uiState.titleColor} leading-normal text-left font-satoshi font-semibold ${uiState.alertBg} p-3 rounded-lg`}>
                            {sentinelResult.explanation}
                          </p>
                        </div>
                      );
                    })()}

                    {/* HEX Copybook box */}
                    <GlassCard padding="md" className="border-slate-200 bg-white">
                      <h4 className="text-[10px] text-slate-500 font-black uppercase tracking-wider mb-2 text-left">COBOL Copybook Hex Frame Intercepted</h4>
                      <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl font-mono text-[10px] text-slate-700 text-left select-all whitespace-pre leading-relaxed overflow-x-auto scrollbar-thin">
                        {sentinelResult.cobol_copybook_hex}
                      </div>
                    </GlassCard>
                  </motion.div>
                ) : (
                  <GlassCard padding="md" className="border-slate-200 bg-slate-50/50 h-full min-h-[400px] flex flex-col items-center justify-center text-center">
                    <Cpu size={48} className="text-slate-300 animate-pulse mb-3" />
                    <h3 className="text-sm font-cabinet font-extrabold text-slate-700">Awaiting Real-Time Interception</h3>
                    <p className="text-xs text-slate-400 mt-1 max-w-[280px]">
                      Paste a Cybercrime warning feed and hit execute to trigger the mainframe low-latency sentinel agent.
                    </p>
                  </GlassCard>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        ) : (
          /* Original Forensic Page Tab */
          <motion.div 
            key="forensic-analyst"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {/* New Investigation */}
            <motion.div variants={fadeInUp}>
              <GlassCard padding="md" className="border-slate-200 bg-white">
                <h3 className="text-xs font-cabinet font-black text-slate-500 uppercase tracking-wider mb-4 text-left">Launch Manual Forensic Deep-Dive</h3>
                <div className="flex flex-wrap gap-3">
                  <input value={txnId} onChange={(e) => setTxnId(e.target.value)} placeholder="Transaction ID (e.g. TXN10001)" className="flex-1 min-w-[200px] px-4 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/40" />
                  <input value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder="Account ID (e.g. IND-195)" className="flex-1 min-w-[200px] px-4 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-cyan-500/40" />
                  <Button variant="primary" onClick={handleStartForensic} loading={startMutation.isPending} icon={<Search size={14} />} className="bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-extrabold">
                    Investigate
                  </Button>
                </div>
              </GlassCard>
            </motion.div>

            {/* Investigation list */}
            <motion.div variants={fadeInUp} className="space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="text-xs font-cabinet font-black text-slate-500 uppercase tracking-wider">Investigation History Ledger</h3>
                <button 
                  onClick={() => refetch()}
                  className="flex items-center gap-1 text-[10px] text-indigo-600 font-bold hover:underline"
                >
                  <RefreshCw size={10} />
                  Refresh
                </button>
              </div>

              {isLoading ? (
                <div className="flex justify-center py-12"><Loader2 className="animate-spin text-indigo-600" /></div>
              ) : !investigations?.length ? (
                <p className="text-slate-400 text-sm text-center py-12">No manual investigations registered yet.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {investigations.map((inv) => (
                    <GlassCard key={inv.id} padding="md" className="border-slate-200 bg-white hover:shadow-md transition-all text-left">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs font-mono font-bold text-slate-800">{inv.id.slice(0, 12)}...</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">Account ID under audit: <span className="font-mono font-extrabold text-indigo-600">{inv.account_id}</span></p>
                        </div>
                        <div className="flex items-center gap-3">
                          {inv.final_risk_score !== undefined && (
                            <span className="text-xs font-black text-cyan-600">{(inv.final_risk_score * 100).toFixed(0)}% risk</span>
                          )}
                          <Badge variant={inv.status === 'completed' ? 'green' : inv.status === 'failed' ? 'red' : 'amber'} size="sm" pulse={inv.status === 'processing'}>
                            {inv.status}
                          </Badge>
                        </div>
                      </div>
                      {inv.verdict && (
                        <p className="text-[10px] font-satoshi font-semibold text-slate-600 mt-2.5 pt-2 border-t border-slate-100 leading-normal">
                          {inv.verdict}
                        </p>
                      )}
                    </GlassCard>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
