/* ═══════════════════════════════════════════════════════════════
   STAT CARD — Animated KPI metric card
   ═══════════════════════════════════════════════════════════════ */

import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { useEffect, type ReactNode } from 'react';
import { GlassCard } from './GlassCard';

interface StatCardProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  icon?: ReactNode;
  trend?: { value: number; direction: 'up' | 'down' };
  variant?: 'cyan' | 'purple' | 'green' | 'red' | 'amber';
  format?: 'number' | 'currency' | 'percent';
}

const accentColors = {
  cyan: 'text-cyan-400',
  purple: 'text-purple-400',
  green: 'text-green-400',
  red: 'text-red-400',
  amber: 'text-amber-400',
};

const iconBgs = {
  cyan: 'bg-cyan-500/10',
  purple: 'bg-purple-500/10',
  green: 'bg-green-500/10',
  red: 'bg-red-500/10',
  amber: 'bg-amber-500/10',
};

function AnimatedNumber({ value, format = 'number' }: { value: number; format?: string }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => {
    if (format === 'currency') return `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    if (format === 'percent') return `${v.toFixed(1)}%`;
    if (v >= 1000) return v.toLocaleString('en-IN', { maximumFractionDigits: 0 });
    return v.toFixed(v % 1 === 0 ? 0 : 2);
  });

  useEffect(() => {
    const controls = animate(count, value, {
      duration: 1.5,
      ease: [0.16, 1, 0.3, 1],
    });
    return controls.stop;
  }, [value, count]);

  return <motion.span>{rounded}</motion.span>;
}

export function StatCard({
  label,
  value,
  prefix,
  suffix,
  icon,
  trend,
  variant = 'cyan',
  format = 'number',
}: StatCardProps) {
  return (
    <GlassCard hover padding="md" className="relative overflow-hidden">
      {/* Ambient glow */}
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full blur-3xl opacity-10 ${
        variant === 'cyan' ? 'bg-cyan-500' :
        variant === 'purple' ? 'bg-purple-500' :
        variant === 'green' ? 'bg-green-500' :
        variant === 'red' ? 'bg-red-500' :
        'bg-amber-500'
      }`} />

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-white/50 uppercase tracking-widest mb-2">{label}</p>
          <p className={`text-3xl font-bold tracking-tight ${accentColors[variant]}`}>
            {prefix}
            <AnimatedNumber value={value} format={format} />
            {suffix}
          </p>
          {trend && (
            <p className={`text-xs mt-2 font-medium ${
              trend.direction === 'up' ? 'text-green-400' : 'text-red-400'
            }`}>
              {trend.direction === 'up' ? '↑' : '↓'} {trend.value}%
              <span className="text-white/30 ml-1">vs last hour</span>
            </p>
          )}
        </div>
        {icon && (
          <div className={`w-10 h-10 rounded-lg ${iconBgs[variant]} flex items-center justify-center ${accentColors[variant]}`}>
            {icon}
          </div>
        )}
      </div>
    </GlassCard>
  );
}
