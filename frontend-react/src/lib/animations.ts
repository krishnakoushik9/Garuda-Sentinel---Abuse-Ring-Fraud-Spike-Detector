/* ═══════════════════════════════════════════════════════════════
   FRAMER MOTION VARIANTS — Reusable animation presets
   ═══════════════════════════════════════════════════════════════ */

import type { Variants, Transition } from 'framer-motion';

// ── Shared transitions ──
export const spring: Transition = {
  type: 'spring',
  stiffness: 300,
  damping: 30,
};

export const smoothSpring: Transition = {
  type: 'spring',
  stiffness: 100,
  damping: 20,
};

export const slowSpring: Transition = {
  type: 'spring',
  stiffness: 60,
  damping: 15,
};

// ── Fade variants ──
export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.6 } },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] } },
};

export const fadeInDown: Variants = {
  hidden: { opacity: 0, y: -30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

export const fadeInLeft: Variants = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

export const fadeInRight: Variants = {
  hidden: { opacity: 0, x: 40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

// ── Scale variants ──
export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.5 },
  visible: { opacity: 1, scale: 1, transition: spring },
};

// ── Stagger container ──
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

export const staggerContainerSlow: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

// ── Card hover ──
export const cardHover = {
  rest: {
    scale: 1,
    y: 0,
    transition: smoothSpring,
  },
  hover: {
    scale: 1.02,
    y: -4,
    transition: smoothSpring,
  },
};

// ── Page transition ──
export const pageTransition: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
  exit: { opacity: 0, y: -20, transition: { duration: 0.3 } },
};

// ── Cinematic reveal ──
export const cinematicReveal: Variants = {
  hidden: {
    opacity: 0,
    y: 60,
    filter: 'blur(10px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: { duration: 1, ease: [0.16, 1, 0.3, 1] },
  },
};

// ── 3D card ──
export const card3D: Variants = {
  hidden: {
    opacity: 0,
    rotateX: 15,
    rotateY: -15,
    scale: 0.9,
  },
  visible: {
    opacity: 1,
    rotateX: 0,
    rotateY: 0,
    scale: 1,
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
  },
};

// ── Glow pulse ──
export const glowPulse: Variants = {
  initial: { boxShadow: '0 0 0px rgba(0, 240, 255, 0)' },
  animate: {
    boxShadow: [
      '0 0 20px rgba(0, 240, 255, 0.1)',
      '0 0 40px rgba(0, 240, 255, 0.2)',
      '0 0 20px rgba(0, 240, 255, 0.1)',
    ],
    transition: { duration: 2, repeat: Infinity },
  },
};
