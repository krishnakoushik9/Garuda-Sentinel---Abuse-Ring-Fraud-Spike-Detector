/* ═══════════════════════════════════════════════════════════════
   CHANNEL INTELLIGENCE — Interactive channel explorer section
   (Repurposed DigitalWallet concept)
   ═══════════════════════════════════════════════════════════════ */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Smartphone,
  ArrowRightLeft,
  Banknote,
  CreditCard,
  Wallet,
  Store,
  Building,
  Cpu,
} from 'lucide-react';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { fadeInUp } from '@/lib/animations';

const channels = [
  {
    id: 'UPI',
    icon: Smartphone,
    color: 'cyan',
    stats: { volume: 245000, fraud: 1842, suspiciousAccounts: 156, riskScore: 0.72 },
  },
  {
    id: 'NEFT',
    icon: ArrowRightLeft,
    color: 'purple',
    stats: { volume: 89000, fraud: 423, suspiciousAccounts: 67, riskScore: 0.45 },
  },
  {
    id: 'IMPS',
    icon: Banknote,
    color: 'green',
    stats: { volume: 156000, fraud: 1204, suspiciousAccounts: 98, riskScore: 0.61 },
  },
  {
    id: 'CARD',
    icon: CreditCard,
    color: 'amber',
    stats: { volume: 312000, fraud: 2105, suspiciousAccounts: 234, riskScore: 0.68 },
  },
  {
    id: 'WALLET',
    icon: Wallet,
    color: 'red',
    stats: { volume: 78000, fraud: 312, suspiciousAccounts: 45, riskScore: 0.38 },
  },
  {
    id: 'MERCHANT',
    icon: Store,
    color: 'blue',
    stats: { volume: 567000, fraud: 3456, suspiciousAccounts: 289, riskScore: 0.54 },
  },
  {
    id: 'ATM',
    icon: Building,
    color: 'purple',
    stats: { volume: 45000, fraud: 178, suspiciousAccounts: 23, riskScore: 0.33 },
  },
  {
    id: 'RTGS',
    icon: Cpu,
    color: 'cyan',
    stats: { volume: 12000, fraud: 56, suspiciousAccounts: 8, riskScore: 0.82 },
  },
];

const colorMap: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30', glow: 'shadow-cyan-500/20' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30', glow: 'shadow-purple-500/20' },
  green: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30', glow: 'shadow-green-500/20' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30', glow: 'shadow-amber-500/20' },
  red: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', glow: 'shadow-red-500/20' },
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', glow: 'shadow-blue-500/20' },
};

export function ChannelIntelligence() {
  const [selectedChannel, setSelectedChannel] = useState(channels[0]);
  const colors = colorMap[selectedChannel.color];

  return (
    <section className="relative py-32 px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <SectionHeader
          eyebrow="Channel Intelligence"
          title={`EVERY CHANNEL.\nONE INTELLIGENCE.`}
          subtitle="Monitor fraud patterns across all banking channels with unified risk scoring and real-time alert generation."
        />

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Channel selector */}
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-4 gap-3"
          >
            {channels.map((channel) => {
              const c = colorMap[channel.color];
              const isActive = selectedChannel.id === channel.id;
              return (
                <motion.button
                  key={channel.id}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setSelectedChannel(channel)}
                  className={`
                    relative flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-300 cursor-pointer
                    ${isActive
                      ? `${c.bg} ${c.border} shadow-lg ${c.glow}`
                      : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05]'
                    }
                  `}
                >
                  <channel.icon size={20} className={isActive ? c.text : 'text-white/40'} />
                  <span className={`text-xs font-semibold tracking-wide ${isActive ? c.text : 'text-white/40'}`}>
                    {channel.id}
                  </span>
                </motion.button>
              );
            })}
          </motion.div>

          {/* Stats display */}
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedChannel.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              className={`rounded-2xl border ${colors.border} bg-card/50 backdrop-blur-xl p-8`}
            >
              <div className="flex items-center gap-4 mb-8">
                <div className={`w-14 h-14 rounded-xl ${colors.bg} flex items-center justify-center`}>
                  <selectedChannel.icon size={28} className={colors.text} />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">{selectedChannel.id} Channel</h3>
                  <p className="text-sm text-white/40">Real-time intelligence feed</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Transaction Volume', value: selectedChannel.stats.volume.toLocaleString() },
                  { label: 'Fraud Volume', value: selectedChannel.stats.fraud.toLocaleString() },
                  { label: 'Suspicious Accounts', value: selectedChannel.stats.suspiciousAccounts.toString() },
                  { label: 'Risk Score', value: (selectedChannel.stats.riskScore * 100).toFixed(0) + '%' },
                ].map((stat) => (
                  <div key={stat.label} className="p-4 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                    <p className="text-xs text-white/40 uppercase tracking-wider mb-1">{stat.label}</p>
                    <p className={`text-2xl font-bold ${colors.text}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Risk bar */}
              <div className="mt-6 pt-4 border-t border-white/[0.06]">
                <div className="flex justify-between text-xs text-white/40 mb-2">
                  <span>Risk Level</span>
                  <span>{(selectedChannel.stats.riskScore * 100).toFixed(0)}%</span>
                </div>
                <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${selectedChannel.stats.riskScore * 100}%` }}
                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    className={`h-full rounded-full ${
                      selectedChannel.stats.riskScore > 0.7
                        ? 'bg-gradient-to-r from-red-500 to-red-600'
                        : selectedChannel.stats.riskScore > 0.5
                        ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                        : 'bg-gradient-to-r from-green-500 to-emerald-500'
                    }`}
                  />
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}
