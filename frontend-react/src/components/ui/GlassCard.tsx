/* ═══════════════════════════════════════════════════════════════
   GLASS CARD — Glassmorphism card with glow effects
   ═══════════════════════════════════════════════════════════════ */

import { motion } from 'framer-motion';
import type { ReactNode, HTMLAttributes } from 'react';
import { cardHover } from '@/lib/animations';

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
  variant?: 'default' | 'cyan' | 'purple' | 'strong';
  hover?: boolean;
  glow?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const glassVariants = {
  default: 'glass',
  cyan: 'glass-cyan',
  purple: 'glass-purple',
  strong: 'glass-strong',
};

const glowVariants = {
  default: 'glow-cyan',
  cyan: 'glow-cyan',
  purple: 'glow-purple',
  strong: 'glow-cyan',
};

const paddings = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export function GlassCard({
  children,
  variant = 'default',
  hover = true,
  glow = false,
  padding = 'md',
  className = '',
  ...props
}: GlassCardProps) {
  return (
    <motion.div
      variants={hover ? cardHover : undefined}
      initial={hover ? 'rest' : undefined}
      whileHover={hover ? 'hover' : undefined}
      className={`
        rounded-xl ${glassVariants[variant]}
        ${glow ? glowVariants[variant] : ''}
        ${paddings[padding]}
        ${className}
      `}
      {...(props as any)}
    >
      {children}
    </motion.div>
  );
}
