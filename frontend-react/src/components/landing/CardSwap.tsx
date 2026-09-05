/* ═══════════════════════════════════════════════════════════════
   CARD SWAP — 3D animated card carousel for hero section
   Showcases platform capabilities with perspective & depth
   ═══════════════════════════════════════════════════════════════ */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  Users,
  ArrowRightLeft,
  AlertTriangle,
  TrendingUp,
  Radio,
} from 'lucide-react';

const cards = [
  {
    title: 'MULE DETECTION ENGINE',
    description: 'Pattern-based identification of mule account networks using 8 distinct behavioral signals.',
    icon: Users,
    gradient: 'from-cyan-500/20 to-blue-600/20',
    borderColor: 'border-cyan-500/30',
    iconColor: 'text-cyan-400',
    stat: '42 Active Mules',
  },
  {
    title: 'FRAUD INTELLIGENCE FEED',
    description: 'Real-time threat detection with XGBoost ML scoring and multi-agent investigation pipeline.',
    icon: Shield,
    gradient: 'from-purple-500/20 to-pink-600/20',
    borderColor: 'border-purple-500/30',
    iconColor: 'text-purple-400',
    stat: '0.94 Avg Precision',
  },
  {
    title: 'CROSS-CHANNEL TRACKING',
    description: 'Unified monitoring across UPI, NEFT, IMPS, RTGS, Card, ATM, and Merchant channels.',
    icon: ArrowRightLeft,
    gradient: 'from-green-500/20 to-emerald-600/20',
    borderColor: 'border-green-500/30',
    iconColor: 'text-green-400',
    stat: '8 Channels Live',
  },
  {
    title: 'EWS MONITORING',
    description: 'Early Warning System with velocity scoring, dormancy detection, and rapid-fund triggers.',
    icon: AlertTriangle,
    gradient: 'from-amber-500/20 to-orange-600/20',
    borderColor: 'border-amber-500/30',
    iconColor: 'text-amber-400',
    stat: '24/7 Scanning',
  },
  {
    title: 'MONEY FLOW ANALYSIS',
    description: 'Multi-hop downstream and upstream fund tracing with contamination radius mapping.',
    icon: TrendingUp,
    gradient: 'from-red-500/20 to-rose-600/20',
    borderColor: 'border-red-500/30',
    iconColor: 'text-red-400',
    stat: '10-Hop Depth',
  },
  {
    title: 'REGULATORY INTELLIGENCE',
    description: 'Integrated CRILC, NCRP/I4C, STR generation, and RBI compliance monitoring.',
    icon: Radio,
    gradient: 'from-blue-500/20 to-indigo-600/20',
    borderColor: 'border-blue-500/30',
    iconColor: 'text-blue-400',
    stat: 'RBI Compliant',
  },
];

export function CardSwap() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % cards.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full h-[500px]" style={{ perspective: '1200px' }}>
      {/* Ambient glow behind cards */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-64 h-64 rounded-full bg-cyan-500/10 blur-[100px]" />
        <div className="absolute w-48 h-48 rounded-full bg-purple-500/10 blur-[80px] translate-x-20 translate-y-10" />
      </div>

      <AnimatePresence mode="popLayout">
        {cards.map((card, index) => {
          const offset = (index - activeIndex + cards.length) % cards.length;
          const isActive = offset === 0;
          const zIndex = cards.length - offset;

          return (
            <motion.div
              key={card.title}
              layout
              initial={{ opacity: 0, scale: 0.8, rotateY: 30 }}
              animate={{
                opacity: offset < 3 ? 1 - offset * 0.3 : 0,
                scale: 1 - offset * 0.08,
                y: offset * 30,
                x: offset * 15,
                rotateY: offset * -5,
                rotateX: offset * 2,
                zIndex,
              }}
              exit={{ opacity: 0, scale: 0.8, rotateY: -30 }}
              transition={{
                type: 'spring',
                stiffness: 200,
                damping: 25,
                mass: 1,
              }}
              onClick={() => setActiveIndex(index)}
              className={`
                absolute inset-0 w-full max-w-md mx-auto cursor-pointer
                rounded-2xl border bg-gradient-to-br ${card.gradient} ${card.borderColor}
                backdrop-blur-xl overflow-hidden
              `}
              style={{ transformStyle: 'preserve-3d' }}
            >
              <div className="p-8 h-full flex flex-col justify-between relative">
                {/* Top: Icon + Title */}
                <div>
                  <div className={`w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-6 ${card.iconColor}`}>
                    <card.icon size={24} />
                  </div>
                  <h3 className="text-xl font-bold text-white tracking-wide mb-3">
                    {card.title}
                  </h3>
                  <p className="text-sm text-white/60 leading-relaxed">
                    {card.description}
                  </p>
                </div>

                {/* Bottom: Stat */}
                <div className="mt-6 pt-4 border-t border-white/10">
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-semibold ${card.iconColor}`}>
                      {card.stat}
                    </span>
                    {isActive && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="w-2 h-2 rounded-full bg-green-400 animate-pulse"
                      />
                    )}
                  </div>
                </div>

                {/* Grid overlay */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none" />
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* Dots indicator */}
      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex gap-2">
        {cards.map((_, i) => (
          <button
            key={i}
            onClick={() => setActiveIndex(i)}
            className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
              i === activeIndex ? 'bg-cyan-400 w-6' : 'bg-white/20 hover:bg-white/40'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
