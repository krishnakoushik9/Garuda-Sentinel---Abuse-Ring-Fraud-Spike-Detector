import { motion } from 'framer-motion';
import { X, Check } from 'lucide-react';
import { fadeInUp, staggerContainer } from '@/lib/animations';

const comparisons = [
  { feature: 'Cross-channel intelligence', traditional: false, fds: true },
  { feature: 'Real-time monitoring', traditional: false, fds: true },
  { feature: 'Graph analytics', traditional: false, fds: true },
  { feature: 'Mule detection', traditional: false, fds: true },
  { feature: 'EWS scoring', traditional: false, fds: true },
  { feature: 'Regulatory integration', traditional: false, fds: true },
  { feature: 'Money flow tracing', traditional: false, fds: true },
  { feature: 'COBOL simulation', traditional: false, fds: true },
];

export function FeatureComparison() {
  return (
    <section className="relative py-32 px-6 lg:px-8 bg-neo-yellow">
      <div className="max-w-5xl mx-auto">
        <motion.div variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          <motion.h2 variants={fadeInUp} className="font-display text-5xl md:text-6xl text-black mb-4">
            STOP USING
            <br />
            OUTDATED TOOLS.
          </motion.h2>
          <motion.p variants={fadeInUp} className="text-lg text-black/60 mb-12 max-w-xl">
            Traditional fraud monitoring can't keep up. See how Fraud Intelligence Aegis FDS compares.
          </motion.p>

          <motion.div variants={fadeInUp} className="bg-white border-4 border-black shadow-[8px_8px_0px_0px_#000] rounded-lg overflow-hidden">
            <div className="grid grid-cols-3 border-b-4 border-black">
              <div className="p-4 font-bold text-black text-sm">FEATURE</div>
              <div className="p-4 font-bold text-black text-sm text-center border-l-4 border-black">TRADITIONAL</div>
              <div className="p-4 font-bold text-black text-sm text-center border-l-4 border-black bg-black text-yellow-300">Aegis FDS V5.0</div>
            </div>
            {comparisons.map((row) => (
              <div key={row.feature} className="grid grid-cols-3 border-b-2 border-black/20 last:border-b-0">
                <div className="p-4 text-sm font-medium text-black">{row.feature}</div>
                <div className="p-4 flex justify-center border-l-4 border-black">
                  <X size={20} className="text-red-500" />
                </div>
                <div className="p-4 flex justify-center border-l-4 border-black bg-black/5">
                  <Check size={20} className="text-green-600 font-bold" />
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
