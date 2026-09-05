/* ═══════════════════════════════════════════════════════════════
   BUTTON — Cinematic button component with variants
   ═══════════════════════════════════════════════════════════════ */

import { motion } from 'framer-motion';
import type { ReactNode, ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'neo';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  icon?: ReactNode;
  children: ReactNode;
  loading?: boolean;
}

const variants = {
  primary:
    'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/20',
  secondary:
    'bg-white/5 border border-white/10 text-white hover:bg-white/10 hover:border-white/20',
  ghost:
    'bg-transparent text-white/70 hover:text-white hover:bg-white/5',
  danger:
    'bg-gradient-to-r from-red-600 to-red-700 text-white hover:from-red-500 hover:to-red-600',
  neo:
    'bg-yellow-300 text-black font-bold border-2 border-black shadow-[4px_4px_0px_0px_#000] hover:shadow-[2px_2px_0px_0px_#000] hover:translate-x-[2px] hover:translate-y-[2px]',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-8 py-3.5 text-base',
  xl: 'px-10 py-4 text-lg tracking-wide',
};

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  children,
  loading,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: variant === 'neo' ? 1 : 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`
        inline-flex items-center justify-center gap-2 rounded-lg font-semibold
        transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}
      `}
      disabled={loading || props.disabled}
      {...(props as any)}
    >
      {loading ? (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon ? (
        <span className="w-4 h-4">{icon}</span>
      ) : null}
      {children}
    </motion.button>
  );
}
