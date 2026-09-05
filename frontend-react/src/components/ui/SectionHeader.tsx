/* ═══════════════════════════════════════════════════════════════
   SECTION HEADER — Cinematic section headline component
   ═══════════════════════════════════════════════════════════════ */

import { motion } from 'framer-motion';
import { cinematicReveal } from '@/lib/animations';

interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  align?: 'left' | 'center';
  className?: string;
}

export function SectionHeader({ eyebrow, title, subtitle, align = 'center', className = '' }: SectionHeaderProps) {
  return (
    <motion.div
      variants={cinematicReveal}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-100px' }}
      className={`mb-16 ${align === 'center' ? 'text-center' : 'text-left'} ${className}`}
    >
      {eyebrow && (
        <span className="inline-block text-xs font-semibold tracking-[0.3em] uppercase text-cyan-400 mb-4">
          {eyebrow}
        </span>
      )}
      <h2 className="font-display text-4xl md:text-5xl lg:text-6xl text-white leading-none">
        {title.split('\n').map((line, i) => (
          <span key={i}>
            {line}
            {i < title.split('\n').length - 1 && <br />}
          </span>
        ))}
      </h2>
      {subtitle && (
        <p className="mt-6 text-lg text-white/50 max-w-2xl mx-auto leading-relaxed">
          {subtitle}
        </p>
      )}
    </motion.div>
  );
}
