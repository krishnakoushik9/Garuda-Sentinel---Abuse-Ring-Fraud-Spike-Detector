import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Radio, Smartphone, ArrowRightLeft, Banknote, CreditCard, Wallet, Store, Building, Cpu, Sun, Moon } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { useChannelHopAlerts, useChannelStats } from '@/hooks/useApi';
import { staggerContainer, fadeInUp } from '@/lib/animations';
import { useAppStore } from '@/stores/appStore';

const channelIcons: Record<string, any> = {
  UPI: Smartphone, NEFT: ArrowRightLeft, IMPS: Banknote, RTGS: Cpu,
  CARD: CreditCard, ATM: Building, MERCHANT: Store, WALLET: Wallet,
};

const channelData = [
  { id: 'UPI', volume: 245000, fraud: 1842, risk: 0.72, alerts: 156 },
  { id: 'IMPS', volume: 156000, fraud: 1204, risk: 0.61, alerts: 98 },
  { id: 'NEFT', volume: 89000, fraud: 423, risk: 0.45, alerts: 67 },
  { id: 'RTGS', volume: 12000, fraud: 56, risk: 0.82, alerts: 8 },
  { id: 'CARD', volume: 312000, fraud: 2105, risk: 0.68, alerts: 234 },
  { id: 'ATM', volume: 45000, fraud: 178, risk: 0.33, alerts: 23 },
  { id: 'MERCHANT', volume: 567000, fraud: 3456, risk: 0.54, alerts: 289 },
  { id: 'WALLET', volume: 78000, fraud: 312, risk: 0.38, alerts: 45 },
];

// Win98 component for half the page
function Win98Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-2 border-t-[#dfdfdf] border-l-[#dfdfdf] border-b-[#404040] border-r-[#404040] bg-[#c0c0c0]">
      <div className="bg-gradient-to-r from-[#000080] to-[#1084d0] px-2 py-1">
        <span className="text-xs font-bold text-white">{title}</span>
      </div>
      <div className="p-2">{children}</div>
    </div>
  );
}

export default function ChannelsPage() {
  const [selected, setSelected] = useState('UPI');
  const { data: hopAlerts } = useChannelHopAlerts();
  const { data: dbChannelData } = useChannelStats();
  const { theme, toggleTheme } = useAppStore();
  
  const activeChannelData = dbChannelData || channelData;
  const channel = activeChannelData.find(c => c.id === selected) || channelData.find(c => c.id === selected)!;
  const Icon = channelIcons[selected] || Radio;

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Channel Intelligence</h1>
          <p className="text-sm text-white/40 mt-1">Cross-channel monitoring & fraud detection</p>
        </div>
        
        {/* Premium Cinematic Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs font-semibold text-white/70 hover:text-white hover:bg-white/[0.06] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 cursor-pointer self-start sm:self-auto shadow-md"
        >
          {theme === 'light' ? (
            <>
              <Moon size={14} className="text-cyan-600" />
              <span>Switch to Dark Mode</span>
            </>
          ) : (
            <>
              <Sun size={14} className="text-amber-400" />
              <span>Switch to Light Mode</span>
            </>
          )}
        </button>
      </motion.div>

      {/* Channel KPIs - Cinematic */}
      <motion.div variants={fadeInUp} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {activeChannelData.map((ch) => {
          const ChIcon = channelIcons[ch.id] || Radio;
          return (
            <GlassCard
              key={ch.id}
              padding="sm"
              hover
              className={`cursor-pointer ${selected === ch.id ? 'border-cyan-500/40 glow-cyan' : ''}`}
              onClick={() => setSelected(ch.id)}
            >
              <div className="flex items-center gap-2 mb-2">
                <ChIcon size={14} className={selected === ch.id ? 'text-cyan-400' : 'text-white/40'} />
                <span className={`text-xs font-bold ${selected === ch.id ? 'text-cyan-400' : 'text-white/50'}`}>{ch.id}</span>
              </div>
              <p className="text-lg font-bold text-white">{ch.volume.toLocaleString()}</p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[10px] text-white/30">Fraud: {ch.fraud}</span>
                <Badge variant={ch.risk > 0.7 ? 'red' : ch.risk > 0.5 ? 'amber' : 'green'} size="sm">
                  {(ch.risk * 100).toFixed(0)}%
                </Badge>
              </div>
            </GlassCard>
          );
        })}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cinematic detail panel */}
        <motion.div variants={fadeInUp}>
          <AnimatePresence mode="wait">
            <motion.div key={selected} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <GlassCard padding="lg" variant="cyan">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-14 h-14 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                    <Icon size={28} className="text-cyan-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">{selected} Channel</h3>
                    <p className="text-xs text-white/40">Real-time intelligence</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-white/[0.03]">
                    <p className="text-xs text-white/40">Volume</p>
                    <p className="text-2xl font-bold text-cyan-400">{channel.volume.toLocaleString()}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-white/[0.03]">
                    <p className="text-xs text-white/40">Fraud Volume</p>
                    <p className="text-2xl font-bold text-red-400">{channel.fraud.toLocaleString()}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-white/[0.03]">
                    <p className="text-xs text-white/40">Risk Score</p>
                    <p className="text-2xl font-bold text-amber-400">{(channel.risk * 100).toFixed(0)}%</p>
                  </div>
                  <div className="p-4 rounded-lg bg-white/[0.03]">
                    <p className="text-xs text-white/40">Active Alerts</p>
                    <p className="text-2xl font-bold text-purple-400">{channel.alerts}</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Win98 hop alerts panel */}
        <motion.div variants={fadeInUp}>
          <Win98Panel title="⚡ CHANNEL HOP ALERTS — Intelligence Workstation">
            <div className="bg-white max-h-[320px] overflow-y-auto border border-inset">
              {!hopAlerts?.length ? (
                <p className="p-2 text-xs text-gray-500">No channel hop alerts detected</p>
              ) : hopAlerts.map((ha, i) => (
                <div key={i} className="p-2 border-b border-gray-200 text-xs hover:bg-blue-100">
                  <div className="flex justify-between">
                    <span className="font-bold text-blue-800">{ha.account_id}</span>
                    <span className={`font-bold ${ha.risk_level === 'HIGH' ? 'text-red-600' : 'text-orange-600'}`}>{ha.risk_level}</span>
                  </div>
                  <div className="text-gray-600 mt-0.5">
                    Channels: {ha.channels_used?.join(' → ')} | Hops: {ha.hop_count}
                  </div>
                </div>
              ))}
            </div>
          </Win98Panel>
        </motion.div>
      </div>
    </motion.div>
  );
}
