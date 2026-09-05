import { motion } from 'framer-motion';
import { ArrowRight, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { ParticleField } from './ParticleField';
import { cinematicReveal } from '@/lib/animations';

interface FinalCTAProps {
  onLaunch: () => void;
}

export function FinalCTA({ onLaunch }: FinalCTAProps) {
  return (
    <section className="relative py-40 px-6 lg:px-8 overflow-hidden">
      <ParticleField count={40} />
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[500px] h-[500px] rounded-full bg-cyan-500/5 blur-[150px]" />
        <div className="absolute w-[400px] h-[400px] rounded-full bg-purple-500/5 blur-[120px] translate-x-32" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto text-center">
        <motion.div variants={cinematicReveal} initial="hidden" whileInView="visible" viewport={{ once: true }}>
          <h2 className="font-display text-5xl md:text-7xl lg:text-8xl text-white mb-4">
            STOP REACTING
            <br />
            <span className="text-white/30">TO FRAUD.</span>
          </h2>
          <h2 className="font-display text-5xl md:text-7xl lg:text-8xl mb-8">
            <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">START</span>
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">PREDICTING IT.</span>
          </h2>

          <div className="flex flex-wrap justify-center gap-4 mt-12">
            <Button variant="primary" size="xl" icon={<ArrowRight size={18} />} onClick={onLaunch}>
              Launch Intelligence Platform
            </Button>
            <Button variant="secondary" size="lg" icon={<LayoutDashboard size={16} />} onClick={onLaunch}>
              Explore Dashboard
            </Button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
