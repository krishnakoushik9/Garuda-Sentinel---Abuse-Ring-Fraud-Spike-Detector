/* ═══════════════════════════════════════════════════════════════
   PLATFORM OVERVIEW — Cinematic bento grid section
   ═══════════════════════════════════════════════════════════════ */

import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  ArrowRightLeft,
  GitBranch,
  Bell,
  Scale,
  Radio,
} from 'lucide-react';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { fadeInUp, staggerContainer } from '@/lib/animations';

const features = [
  {
    title: 'Overview Command Center',
    description: 'Live KPI monitoring, threat feeds, and fraud heatmaps in one unified dashboard.',
    icon: LayoutDashboard,
    gradient: 'from-cyan-500 to-blue-600',
    span: 'lg:col-span-2 lg:row-span-2',
  },
  {
    title: 'Transaction Intelligence',
    description: 'AG Grid powered analysis of 100K+ transactions with real-time risk scoring.',
    icon: ArrowRightLeft,
    gradient: 'from-purple-500 to-pink-600',
    span: '',
  },
  {
    title: 'Graph Analytics',
    description: 'Force-directed network visualization with community detection and money trail tracing.',
    icon: GitBranch,
    gradient: 'from-green-500 to-emerald-600',
    span: '',
  },
  {
    title: 'Alert Intelligence',
    description: 'Multi-bucket alert management with government tickets, EWS escalations, and STR candidates.',
    icon: Bell,
    gradient: 'from-amber-500 to-orange-600',
    span: 'lg:col-span-2',
  },
  {
    title: 'Regulatory Intelligence',
    description: 'CRILC monitoring, STR queuing, NCRP feed integration, and compliance audit trails.',
    icon: Scale,
    gradient: 'from-red-500 to-rose-600',
    span: '',
  },
  {
    title: 'Channel Intelligence',
    description: 'Cross-channel monitoring across UPI, NEFT, IMPS, RTGS, Card, ATM, and Merchant.',
    icon: Radio,
    gradient: 'from-blue-500 to-indigo-600',
    span: '',
  },
];

export function PlatformOverview() {
  return (
    <section className="relative py-32 px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <SectionHeader
          eyebrow="Platform"
          title={`ONE PLATFORM.\nFULL INVESTIGATION PIPELINE.`}
          subtitle="From transaction ingestion to regulatory compliance — a complete fraud intelligence operating system."
        />

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={fadeInUp}
              className={`group relative rounded-2xl border border-white/[0.06] bg-card overflow-hidden ${feature.span}`}
            >
              {/* Hover gradient overlay */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-[0.08] transition-opacity duration-500`} />

              {/* Content */}
              <div className="relative p-8 h-full flex flex-col">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} bg-opacity-20 flex items-center justify-center mb-6`}>
                  <feature.icon size={24} className="text-white" />
                </div>

                <h3 className="text-lg font-bold text-white mb-3 tracking-wide">
                  {feature.title}
                </h3>
                <p className="text-sm text-white/50 leading-relaxed flex-1">
                  {feature.description}
                </p>

                {/* Bottom line */}
                <div className={`mt-6 h-px bg-gradient-to-r ${feature.gradient} opacity-20 group-hover:opacity-60 transition-opacity`} />
              </div>

              {/* Grid pattern */}
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
