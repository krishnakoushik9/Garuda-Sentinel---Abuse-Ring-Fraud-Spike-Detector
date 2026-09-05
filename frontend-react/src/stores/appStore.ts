/* ═══════════════════════════════════════════════════════════════
   GLOBAL STORE — Zustand store for app-wide state
   ═══════════════════════════════════════════════════════════════ */

import { create } from 'zustand';
import type { SystemStatus } from '@/types/api';

interface AppState {
  // Navigation
  currentPage: string;
  setCurrentPage: (page: string) => void;

  // System status
  systemStatus: SystemStatus;
  setSystemStatus: (status: Partial<SystemStatus>) => void;

  // Landing → Dashboard transition
  hasEnteredPlatform: boolean;
  enterPlatform: () => void;

  // Theme
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  theme: 'dark' | 'light';
  toggleTheme: () => void;

  // Selected entities for drill-down
  selectedAccountId: string | null;
  setSelectedAccountId: (id: string | null) => void;
  selectedTransactionId: string | null;
  setSelectedTransactionId: (id: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: 'overview',
  setCurrentPage: (page) => set({ currentPage: page }),

  systemStatus: {
    cobol: 'online',
    fraudEngine: 'online',
    kafka: 'offline',
    database: 'online',
  },
  setSystemStatus: (status) =>
    set((state) => ({ systemStatus: { ...state.systemStatus, ...status } })),

  hasEnteredPlatform: false,
  enterPlatform: () => set({ hasEnteredPlatform: true }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  theme: (localStorage.getItem('theme') as 'dark' | 'light') || 'dark',
  toggleTheme: () =>
    set((state) => {
      const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', nextTheme);
      if (nextTheme === 'light') {
        document.documentElement.classList.add('light');
      } else {
        document.documentElement.classList.remove('light');
      }
      return { theme: nextTheme };
    }),

  selectedAccountId: null,
  setSelectedAccountId: (id) => set({ selectedAccountId: id }),
  selectedTransactionId: null,
  setSelectedTransactionId: (id) => set({ selectedTransactionId: id }),
}));
