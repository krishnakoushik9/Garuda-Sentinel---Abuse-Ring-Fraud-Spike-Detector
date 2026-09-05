/* ═══════════════════════════════════════════════════════════════
   BADGE — Status & severity indicator badges
   ═══════════════════════════════════════════════════════════════ */

import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'cyan' | 'purple' | 'green' | 'red' | 'amber' | 'neutral';
  size?: 'sm' | 'md';
  pulse?: boolean;
  className?: string;
}

const colors = {
  cyan: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  purple: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  green: 'bg-green-500/15 text-green-400 border-green-500/30',
  red: 'bg-red-500/15 text-red-400 border-red-500/30',
  amber: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  neutral: 'bg-white/5 text-white/60 border-white/10',
};

const sizes = {
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-3 py-1 text-xs',
};

export function Badge({ children, variant = 'cyan', size = 'md', pulse = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full border font-medium uppercase tracking-wider
        ${colors[variant]} ${sizes[size]} ${className}
      `}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
            variant === 'red' ? 'bg-red-400' :
            variant === 'green' ? 'bg-green-400' :
            variant === 'cyan' ? 'bg-cyan-400' :
            variant === 'amber' ? 'bg-amber-400' :
            'bg-white'
          }`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${
            variant === 'red' ? 'bg-red-500' :
            variant === 'green' ? 'bg-green-500' :
            variant === 'cyan' ? 'bg-cyan-500' :
            variant === 'amber' ? 'bg-amber-500' :
            'bg-white'
          }`} />
        </span>
      )}
      {children}
    </span>
  );
}
