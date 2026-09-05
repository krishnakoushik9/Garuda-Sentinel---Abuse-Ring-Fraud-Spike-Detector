import { motion } from 'framer-motion';
import { Server, Brain, Shield, Monitor } from 'lucide-react';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { fadeInUp, staggerContainerSlow } from '@/lib/animations';

const steps = [
  { number: '01', title: 'COBOL BANKING ENGINE', description: 'Legacy core banking simulator generates realistic transaction patterns across 8 channels.', icon: Server, color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30' },
  { number: '02', title: 'FRAUD INTELLIGENCE ENGINE', description: 'XGBoost ML model with multi-agent investigation orchestration scores every transaction.', icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30' },
  { number: '03', title: 'RISK SCORING & EWS', description: 'Early Warning System with velocity analysis, dormancy detection, and risk propagation.', icon: Shield, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  { number: '04', title: 'INVESTIGATOR COMMAND CENTER', description: 'Full-stack intelligence dashboard with graph analytics and compliance monitoring.', icon: Monitor, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
];

export function HowItWorks() {
  return (
    <section className="relative py-32 px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <SectionHeader eyebrow="Architecture" title={`HOW THE SYSTEM\nWORKS`} subtitle="From raw COBOL transactions to actionable intelligence." />
        <motion.div variants={staggerContainerSlow} initial="hidden" whileInView="visible" viewport={{ once: true }} className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {steps.map((step, i) => (
            <motion.div key={step.number} variants={fadeInUp} className="relative">
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-16 -right-4 w-8 h-px bg-white/20 z-10" />
              )}
              <div className="rounded-2xl border border-white/[0.06] bg-card p-8 h-full hover:border-white/10 transition-colors">
                <div className={`text-6xl font-display ${step.color} opacity-20 mb-4`}>{step.number}</div>
                <div className={`w-14 h-14 rounded-xl ${step.bg} ${step.border} flex items-center justify-center mb-6`}>
                  <step.icon size={24} className={step.color} />
                </div>
                <h3 className="text-lg font-bold text-white tracking-wide mb-3">{step.title}</h3>
                <p className="text-sm text-white/50 leading-relaxed">{step.description}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
