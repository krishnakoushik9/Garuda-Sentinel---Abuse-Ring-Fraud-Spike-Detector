/* ═══════════════════════════════════════════════════════════════
   HERO SECTION — Cinematic hero with CardSwap + particles
   ═══════════════════════════════════════════════════════════════ */

import { motion } from 'framer-motion';
import { ArrowRight, Eye } from 'lucide-react';
import { CardSwap } from './CardSwap';
import { ParticleField } from './ParticleField';
import { Button } from '@/components/ui/Button';
import { fadeInUp, staggerContainer } from '@/lib/animations';

interface HeroSectionProps {
  onLaunch: () => void;
  onViewArchitecture: () => void;
}

export function HeroSection({ onLaunch, onViewArchitecture }: HeroSectionProps) {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-void" />
      <ParticleField count={80} />

      {/* Giant floating text */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.03 }}
          transition={{ duration: 2 }}
          className="font-display text-[20vw] leading-none text-white whitespace-nowrap"
        >
          FRAUD
          <br />
          INTELLIGENCE
        </motion.div>
      </div>

      {/* Aurora gradient */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-cyan-500/5 blur-[150px] animate-gradient" />
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-purple-500/5 blur-[150px] animate-gradient" style={{ animationDelay: '-4s' }} />

      {/* Content */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Text content */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Eyebrow */}
            <motion.div variants={fadeInUp} className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-xs font-semibold tracking-[0.3em] uppercase text-cyan-400">
                Intelligence Platform V5.0
              </span>
            </motion.div>

            {/* Headline */}
            <motion.h1 variants={fadeInUp} className="font-display text-5xl md:text-6xl lg:text-7xl text-white">
              BANKING
              <br />
              FRAUD
              <br />
              <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-500 bg-clip-text text-transparent">
                INTELLIGENCE
              </span>
              <br />
              <span className="text-white/40">OPERATING SYSTEM</span>
            </motion.h1>

            {/* Subheading */}
            <motion.p
              variants={fadeInUp}
              className="text-lg text-white/50 max-w-lg leading-relaxed"
            >
              Detect mule accounts, suspicious transaction chains, regulatory risks,
              and cross-channel laundering patterns in real time.
            </motion.p>

            {/* CTAs */}
            <motion.div variants={fadeInUp} className="flex flex-wrap gap-4 pt-4">
              <Button
                variant="primary"
                size="xl"
                icon={<ArrowRight size={18} />}
                onClick={onLaunch}
              >
                Launch Intelligence Platform
              </Button>
              <Button
                variant="secondary"
                size="lg"
                icon={<Eye size={16} />}
                onClick={onViewArchitecture}
              >
                View Architecture
              </Button>
            </motion.div>

            {/* Stats bar */}
            <motion.div
              variants={fadeInUp}
              className="flex gap-8 pt-6 border-t border-white/10"
            >
              {[
                { label: 'Accounts Monitored', value: '100K+' },
                { label: 'Transactions/Day', value: '2.5M' },
                { label: 'Fraud Detection Rate', value: '99.4%' },
              ].map((stat) => (
                <div key={stat.label}>
                  <p className="text-2xl font-bold text-white">{stat.value}</p>
                  <p className="text-xs text-white/40 mt-1">{stat.label}</p>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right: CardSwap */}
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="hidden lg:block"
          >
            <CardSwap />
          </motion.div>
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-[10px] tracking-[0.3em] uppercase text-white/30">Scroll</span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="w-5 h-8 rounded-full border border-white/20 flex justify-center pt-1.5"
        >
          <div className="w-1 h-2 rounded-full bg-white/40" />
        </motion.div>
      </motion.div>
    </section>
  );
}
