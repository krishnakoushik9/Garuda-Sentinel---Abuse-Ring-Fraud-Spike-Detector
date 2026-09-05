import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, AlertTriangle, Shield, FileText, Radio, Search, Loader2, Link2, RefreshCw, X, HelpCircle, CheckCircle2 } from 'lucide-react';
import { useAlerts, useEWSAlerts, useSearchECourts, useTrackECourtsCase } from '@/hooks/useApi';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

function Win98Window({ title, icon: Icon, children, className = '' }: { title: string; icon: any; children: React.ReactNode; className?: string }) {
  return (
    <div className={`border-2 border-t-[#dfdfdf] border-l-[#dfdfdf] border-b-[#404040] border-r-[#404040] bg-[#c0c0c0] rounded-sm shadow-md ${className}`}>
      <div className="bg-gradient-to-r from-[#000080] to-[#1084d0] px-2 py-1 flex items-center gap-2 select-none">
        <Icon size={12} className="text-white shrink-0" />
        <span className="text-xs font-bold text-white flex-1 truncate">{title}</span>
        <div className="flex gap-0.5 shrink-0">
          <button className="w-4 h-3.5 bg-[#c0c0c0] border border-t-white border-l-white border-b-[#404040] border-r-[#404040] text-[8px] font-bold flex items-center justify-center active:border-inset">_</button>
          <button className="w-4 h-3.5 bg-[#c0c0c0] border border-t-white border-l-white border-b-[#404040] border-r-[#404040] text-[8px] font-bold flex items-center justify-center active:border-inset">□</button>
          <button className="w-4 h-3.5 bg-[#c0c0c0] border border-t-white border-l-white border-b-[#404040] border-r-[#404040] text-[8px] font-bold flex items-center justify-center active:border-inset">×</button>
        </div>
      </div>
      <div className="p-2">{children}</div>
    </div>
  );
}

export default function AlertsPage() {
  const { data: alerts, isLoading, refetch } = useAlerts();
  const { data: ewsAlerts } = useEWSAlerts();

  // eCourts workstation state
  const [activeSubTab, setActiveSubTab] = useState<'feed' | 'ecourts'>('feed');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [trackMessage, setTrackMessage] = useState<string | null>(null);
  
  // Case detail modal state
  const [detailCase, setDetailCase] = useState<any | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const searchMutation = useSearchECourts();
  const trackMutation = useTrackECourtsCase();

  const criticalAlerts = alerts?.filter(a => a.severity === 'CRITICAL') ?? [];
  const highAlerts = alerts?.filter(a => a.severity === 'HIGH') ?? [];
  const mediumAlerts = alerts?.filter(a => a.severity === 'MEDIUM' || a.severity === 'LOW') ?? [];

  const handleSearch = async (e?: React.FormEvent, presetQuery?: string) => {
    if (e) e.preventDefault();
    const queryToUse = presetQuery ?? searchQuery;
    if (!queryToUse.trim()) return;

    setIsSearching(true);
    setTrackMessage(null);
    setSearchError(null);
    try {
      const data = await searchMutation.mutateAsync(queryToUse);
      setSearchResults(data.results || []);
    } catch (err: any) {
      console.error(err);
      setSearchError(err.message || "Failed to contact judicial API complex.");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleTrack = async (cnr: string) => {
    setTrackMessage(null);
    try {
      const res = await trackMutation.mutateAsync({ cnr });
      setTrackMessage(res.message);
      // Automatically refresh alerts feed
      refetch();
    } catch (err: any) {
      setTrackMessage(`❌ Integration failed: ${err.message || 'Ledger correlation fault'}`);
    }
  };

  const handleViewDetails = async (alertId: string) => {
    // If it's a tracked CNR eCourts case, it will contain or start with CNR or FE-CNR
    let cnr = '';
    if (alertId.includes('FE-CNR-')) {
      // Reconstruct full cnr or query by cnr
      // Our backend handles custom searches so we'll try to find the CNR
      cnr = alerts?.find(a => a.id === alertId)?.id.replace('FE-CNR-', '') || '';
      // Since event_id uses req.cnr[-8:], we can also lookup via alerts list
    } else {
      cnr = alertId;
    }
    
    // Check if it's a valid eCourts format or search record
    setIsLoadingDetail(true);
    try {
      // Let's resolve the actual CNR from descriptions or try looking up directly
      const alert = alerts?.find(a => a.id === alertId);
      let targetCnr = cnr;
      if (alert && alert.description) {
        const match = alert.description.match(/CNR\s+([A-Z0-9]+)/i);
        if (match) {
          targetCnr = match[1];
        }
      }
      
      const res = await fetch(`/api/v1/alerts/ecourts/case/${targetCnr}`);
      if (res.ok) {
        const data = await res.json();
        setDetailCase(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const loadPreset = (cnr: string) => {
    setSearchQuery(cnr);
    handleSearch(undefined, cnr);
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-4 text-left">
      <motion.div variants={fadeInUp} className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Bell size={20} className="text-amber-400" />
          <h1 className="text-2xl font-bold text-white">Alert Intelligence Workstation</h1>
        </div>
        <button 
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-1 bg-[#c0c0c0] border-2 border-t-white border-l-white border-b-[#404040] border-r-[#404040] text-xs font-bold text-slate-800 hover:bg-slate-200 active:border-inset"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          Sync Core Telemetry
        </button>
      </motion.div>

      <motion.div variants={fadeInUp} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Critical Alerts / eCourts Workstation */}
        <Win98Window title="⚠ CRITICAL ALERTS — Government Tickets & Judicial Intelligence" icon={AlertTriangle}>
          <div className="flex bg-[#808080] p-0.5 border-b border-gray-400 mb-2 gap-0.5 select-none">
            <button 
              onClick={() => setActiveSubTab('feed')}
              className={`px-3 py-1 text-xs font-bold transition-all border ${
                activeSubTab === 'feed'
                  ? 'bg-[#c0c0c0] border-t-white border-l-white border-b-transparent border-r-[#404040] text-black shadow-sm'
                  : 'bg-[#b0b0b0] border-transparent text-gray-700 hover:text-black'
              }`}
            >
              Active Government Tickets ({criticalAlerts.length})
            </button>
            <button 
              onClick={() => setActiveSubTab('ecourts')}
              className={`px-3 py-1 text-xs font-bold transition-all border ${
                activeSubTab === 'ecourts'
                  ? 'bg-[#c0c0c0] border-t-white border-l-white border-b-transparent border-r-[#404040] text-black shadow-sm'
                  : 'bg-[#b0b0b0] border-transparent text-gray-700 hover:text-black'
              }`}
            >
              ⚖ eCourts Live Workstation
            </button>
          </div>

          <AnimatePresence mode="wait">
            {activeSubTab === 'feed' ? (
              <motion.div 
                key="feed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-white min-h-[220px] max-h-[300px] overflow-y-auto border border-inset"
              >
                {criticalAlerts.length === 0 ? (
                  <div className="p-8 text-center text-xs text-gray-500 font-mono">
                    🚫 No active critical cybercrime or legal complaints found in ledger.
                  </div>
                ) : criticalAlerts.map((a) => {
                  const isECourts = a.id.includes('CNR') || (a.fraud_type && a.fraud_type.toLowerCase().includes('court'));
                  return (
                    <div 
                      key={a.id} 
                      onClick={() => handleViewDetails(a.id)}
                      className={`p-2.5 border-b border-gray-200 text-xs hover:bg-blue-100 cursor-pointer transition-all flex justify-between items-start gap-4 ${isECourts ? 'bg-indigo-50/50 border-l-2 border-l-indigo-600' : ''}`}
                    >
                      <div className="space-y-0.5 flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-extrabold text-red-700 uppercase tracking-tight">{a.fraud_type}</span>
                          {isECourts && (
                            <span className="px-1.5 py-0.2 bg-indigo-600 text-white rounded text-[8px] font-black uppercase tracking-wider">
                              eCourts Sync
                            </span>
                          )}
                        </div>
                        <p className="text-gray-600 truncate font-mono text-[11px]">
                          Holder ID: <span className="font-bold text-gray-800">{a.account_id}</span>
                        </p>
                        <p className="text-[10px] text-gray-500 truncate leading-relaxed">
                          {a.description}
                        </p>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="font-black text-red-600 font-mono">₹{a.amount?.toLocaleString()}</div>
                        <span className="text-[9px] px-1 bg-red-100 text-red-700 font-bold border border-red-300">
                          {a.channel || 'CRITICAL'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </motion.div>
            ) : (
              <motion.div 
                key="ecourts"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-3 font-mono text-xs"
              >
                {/* Suggestions */}
                <div className="bg-slate-100 border border-inset p-2 rounded-sm space-y-1">
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                    <HelpCircle size={10} /> Live CNR preset suggestions for instant validation:
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <button 
                      onClick={() => loadPreset('DLHC010351552024')} 
                      className="px-2 py-0.5 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 text-indigo-700 font-bold rounded-sm text-[10px]"
                    >
                      Aarav Sharma (Delhi High Court)
                    </button>
                    <button 
                      onClick={() => loadPreset('HCBM050012342023')} 
                      className="px-2 py-0.5 bg-orange-50 border border-orange-200 hover:bg-orange-100 text-orange-700 font-bold rounded-sm text-[10px]"
                    >
                      Aditi Patel (Bombay High Court)
                    </button>
                    <button 
                      onClick={() => loadPreset('DLND020047882015')} 
                      className="px-2 py-0.5 bg-slate-200 border border-slate-300 hover:bg-slate-300 text-slate-700 font-bold rounded-sm text-[10px]"
                    >
                      Arun Jaitley vs Kejriwal
                    </button>
                  </div>
                </div>

                {/* Search query form */}
                <form onSubmit={handleSearch} className="flex gap-2">
                  <input 
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter Indian Court CNR (e.g. DLHC010351552024) or litigant name..."
                    className="flex-1 px-3 py-1.5 bg-white border border-inset focus:outline-none focus:ring-1 focus:ring-blue-700 text-xs"
                  />
                  <button 
                    type="submit"
                    disabled={isSearching}
                    className="px-4 py-1 bg-[#c0c0c0] border-2 border-t-white border-l-white border-b-[#404040] border-r-[#404040] font-bold text-slate-800 hover:bg-slate-200 flex items-center gap-1 active:border-inset"
                  >
                    {isSearching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
                    Lookup
                  </button>
                </form>

                {/* Success message banner */}
                {trackMessage && (
                  <div className="p-2 bg-emerald-50 border-2 border-emerald-500 rounded text-emerald-900 font-bold text-[11px] leading-normal flex items-start gap-1.5 animate-fadeIn">
                    <CheckCircle2 size={14} className="text-emerald-700 shrink-0 mt-0.5" />
                    <div>{trackMessage}</div>
                  </div>
                )}

                {/* Search results list */}
                <div className="bg-white border border-inset min-h-[140px] max-h-[220px] overflow-y-auto">
                  {searchError && (
                    <div className="p-4 text-center text-red-600 text-[11px] font-bold flex flex-col items-center justify-center gap-1.5 font-mono">
                      <AlertTriangle size={16} className="text-red-600 shrink-0" />
                      <span>{searchError}</span>
                    </div>
                  )}
                  {searchMutation.isIdle && !searchResults.length && !searchError && (
                    <p className="p-6 text-center text-gray-500 text-[11px]">
                      Awaiting query submission. Enter a case CNR or name to search eCourts India records.
                    </p>
                  )}
                  {isSearching && (
                    <div className="p-6 text-center text-gray-500 flex flex-col items-center justify-center gap-2">
                      <Loader2 size={24} className="animate-spin text-indigo-600" />
                      <span>Contacting eCourts India API partner portal...</span>
                    </div>
                  )}
                  {!isSearching && !searchError && searchResults.map((r) => (
                    <div key={r.cnr} className="p-2.5 border-b border-gray-200 flex justify-between items-start gap-4">
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-extrabold text-blue-900 truncate text-[11px]">{r.title}</span>
                          <span className="text-[9px] px-1 bg-blue-100 border border-blue-200 text-blue-800 font-bold shrink-0">
                            {r.case_type}
                          </span>
                        </div>
                        <div className="text-[10px] text-gray-500 space-y-0.5">
                          <p>CNR: <span className="font-bold text-gray-700 select-all">{r.cnr}</span></p>
                          <p>Court: {r.court_name} | Filed: {r.filing_date}</p>
                          <div className="flex gap-1 flex-wrap pt-0.5">
                            {r.keywords?.map((k: string) => (
                              <span key={k} className="text-[8px] bg-slate-100 px-1 py-0.2 text-slate-600 rounded">
                                #{k}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      <button 
                        onClick={() => handleTrack(r.cnr)}
                        disabled={trackMutation.isPending}
                        className="px-2.5 py-1 bg-gradient-to-r from-cyan-700 to-indigo-700 hover:from-cyan-600 hover:to-indigo-600 text-white font-extrabold border border-indigo-900 shadow-sm flex items-center gap-1 text-[9px] rounded-sm disabled:opacity-50 shrink-0"
                      >
                        {trackMutation.isPending ? (
                          <Loader2 size={10} className="animate-spin" />
                        ) : (
                          <Link2 size={10} />
                        )}
                        Sync & Track
                      </button>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Win98Window>

        {/* High Alerts */}
        <Win98Window title="🔴 HIGH PRIORITY — Cross Channel Alerts" icon={Radio}>
          <div className="bg-white min-h-[260px] max-h-[300px] overflow-y-auto border border-inset">
            {highAlerts.length === 0 ? (
              <p className="p-2 text-xs text-gray-500">No high priority alerts</p>
            ) : highAlerts.map((a) => (
              <div key={a.id} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100 cursor-pointer">
                <div className="flex justify-between">
                  <span className="font-bold text-orange-700">{a.fraud_type}</span>
                  <span className="text-gray-500">Risk: {((a.risk_score ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="text-gray-600 mt-0.5">{a.account_id} | TXN: {a.transaction_id}</div>
              </div>
            ))}
          </div>
        </Win98Window>

        {/* EWS Alerts */}
        <Win98Window title="⏰ EWS ESCALATIONS — Early Warning Signals" icon={Shield}>
          <div className="bg-white min-h-[220px] max-h-[250px] overflow-y-auto border border-inset">
            {!ewsAlerts?.length ? (
              <p className="p-2 text-xs text-gray-500">No EWS alerts</p>
            ) : ewsAlerts.map((a, i) => (
              <div key={i} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100 cursor-pointer">
                <div className="flex justify-between">
                  <span className="font-bold text-blue-800">{a.account_id}</span>
                  <span className="text-red-600 font-bold">EWS: {(a.ews_score * 100).toFixed(0)}%</span>
                </div>
                <div className="text-gray-600 mt-0.5">{a.triggered_signals?.join(', ')}</div>
              </div>
            ))}
          </div>
        </Win98Window>

        {/* STR/Watchlist */}
        <Win98Window title="📋 STR CANDIDATES & WATCHLIST" icon={FileText}>
          <div className="bg-white min-h-[220px] max-h-[250px] overflow-y-auto border border-inset">
            {mediumAlerts.length === 0 ? (
              <p className="p-2 text-xs text-gray-500">No STR candidates</p>
            ) : mediumAlerts.map((a) => (
              <div key={a.id} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100 cursor-pointer">
                <div className="flex justify-between">
                  <span className="font-bold">{a.fraud_type}</span>
                  <span className="text-gray-500">{new Date(a.timestamp).toLocaleDateString()}</span>
                </div>
                <div className="text-gray-600 mt-0.5">{a.account_id}</div>
              </div>
            ))}
          </div>
        </Win98Window>
      </motion.div>

      {/* Case Details Modal Window */}
      <AnimatePresence>
        {detailCase && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-[500px]"
            >
              <Win98Window 
                title={`⚖ eCourts Indian Case Profile — ${detailCase.cnr}`} 
                icon={Shield}
              >
                <div className="bg-[#c0c0c0] font-mono text-xs space-y-3">
                  <div className="bg-white border border-inset p-3 space-y-1.5 text-[11px]">
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">CNR Number:</span>
                      <span className="text-gray-900 font-extrabold select-all">{detailCase.cnr}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">Case Category:</span>
                      <span className="text-gray-900 font-bold">{detailCase.case_type}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">Litigants (Parties):</span>
                      <span className="text-blue-900 font-extrabold text-right truncate max-w-[280px]">{detailCase.litigants}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">Court Facility:</span>
                      <span className="text-gray-800 font-bold text-right truncate max-w-[280px]">{detailCase.court_name}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">Next Hearing:</span>
                      <span className="text-indigo-800 font-bold">{detailCase.next_hearing || "N/A"}</span>
                    </div>
                    <div className="flex justify-between border-b border-gray-200 pb-1">
                      <span className="font-bold text-gray-500">Judicial Status:</span>
                      <span className="px-1.5 py-0.2 bg-red-100 border border-red-300 text-red-800 font-bold text-[9px]">
                        {detailCase.status}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-bold text-gray-500">Correlated Account:</span>
                      <span className="text-red-700 font-extrabold underline">{detailCase.account_id || "ACC003453"}</span>
                    </div>
                  </div>

                  <div className="bg-[#000080] text-white p-0.5 text-[9px] font-bold uppercase tracking-wider text-center select-none">
                    📜 AI Judicial Assistant briefing summary
                  </div>
                  <div className="bg-[#f5f5f5] border border-inset p-2.5 text-[11px] leading-relaxed text-slate-800 max-h-[100px] overflow-y-auto scrollbar-thin">
                    {detailCase.ai_summary}
                  </div>

                  <div className="bg-red-50 border-2 border-red-500 p-2 text-[10px] leading-normal text-red-900 font-bold flex gap-2">
                    <AlertTriangle size={14} className="text-red-700 shrink-0 mt-0.5 animate-pulse" />
                    <div>
                      CBS SENTINEL ACTION TRIGGERED: Associated Account status set to GOVT_FLAGGED. 
                      Funds interception and ledger clearing restrictions enforced automatically.
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-1 border-t border-gray-300">
                    <button 
                      onClick={() => setDetailCase(null)}
                      className="px-4 py-1 bg-[#c0c0c0] border-2 border-t-white border-l-white border-b-[#404040] border-r-[#404040] font-bold text-xs text-slate-800 hover:bg-slate-200 active:border-inset"
                    >
                      Dismiss Case Profile
                    </button>
                  </div>
                </div>
              </Win98Window>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
