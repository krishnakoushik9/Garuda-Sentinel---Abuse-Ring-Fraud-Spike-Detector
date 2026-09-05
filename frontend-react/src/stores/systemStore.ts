import { create } from 'zustand';

export interface GeneratorStatus {
  running: boolean;
  pid: number | null;
  logs: string[];
}

export interface UserProfile {
  name: string;
  email: string;
  avatar_url: string;
  user_id?: string;
  updated_at?: string;
}

export interface CobolStatus {
  status: string;
  running: boolean;
  pid: number | null;
  accounts_count: number;
  transactions_count: number;
  fraud_events_count: number;
}

export interface RealTimeMetrics {
  accounts: number;
  transactions: number;
  alerts: number;
  mules: number;
  ewsEvents: number;
  nodes: number;
  edges: number;
}

interface SystemState {
  dataSource: 'COBOL_SYNTHETIC' | 'REGULATORY_FEED';
  generatorStatus: GeneratorStatus;
  profile: UserProfile;
  cobolStatus: CobolStatus;
  realTimeMetrics: RealTimeMetrics;
  
  // Actions
  setDataSource: (source: 'COBOL_SYNTHETIC' | 'REGULATORY_FEED') => void;
  setGeneratorStatus: (status: Partial<GeneratorStatus>) => void;
  setProfile: (profile: Partial<UserProfile>) => void;
  setCobolStatus: (status: Partial<CobolStatus>) => void;
  setRealTimeMetrics: (metrics: Partial<RealTimeMetrics>) => void;
  
  // Async operations
  fetchDataSourceStatus: () => Promise<void>;
  switchDataSource: (source: 'COBOL_SYNTHETIC' | 'REGULATORY_FEED') => Promise<void>;
  fetchGeneratorStatus: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  fetchCobolStatus: () => Promise<void>;
  fetchRealTimeMetrics: () => Promise<void>;
  saveProfile: (name: string, email: string, avatarUrl: string) => Promise<void>;
}

export const useSystemStore = create<SystemState>((set, get) => ({
  dataSource: 'COBOL_SYNTHETIC',
  
  generatorStatus: {
    running: false,
    pid: null,
    logs: []
  },
  
  profile: {
    name: 'Admin User',
    email: 'admin@aegis.com',
    avatar_url: '🧑‍💻'
  },
  
  cobolStatus: {
    status: 'Stopped',
    running: false,
    pid: null,
    accounts_count: 0,
    transactions_count: 0,
    fraud_events_count: 0
  },
  
  realTimeMetrics: {
    accounts: 0,
    transactions: 0,
    alerts: 0,
    mules: 0,
    ewsEvents: 0,
    nodes: 0,
    edges: 0
  },

  setDataSource: (source) => set({ dataSource: source }),
  
  setGeneratorStatus: (status) => set((state) => ({
    generatorStatus: { ...state.generatorStatus, ...status }
  })),
  
  setProfile: (profile) => set((state) => ({
    profile: { ...state.profile, ...profile }
  })),
  
  setCobolStatus: (status) => set((state) => ({
    cobolStatus: { ...state.cobolStatus, ...status }
  })),
  
  setRealTimeMetrics: (metrics) => set((state) => ({
    realTimeMetrics: { ...state.realTimeMetrics, ...metrics }
  })),

  fetchDataSourceStatus: async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/datasource/status');
      if (res.ok) {
        const data = await res.json();
        set({ dataSource: data.active_source });
      }
    } catch (err) {
      console.error('Failed to fetch data source status:', err);
    }
  },

  switchDataSource: async (source) => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/datasource/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source })
      });
      if (res.ok) {
        const data = await res.json();
        set({ dataSource: data.active_source });
      }
    } catch (err) {
      console.error('Failed to switch data source:', err);
    }
  },

  fetchGeneratorStatus: async () => {
    try {
      const res = await fetch('http://localhost:8000/api/generator/status');
      if (res.ok) {
        const data = await res.json();
        set((state) => ({
          generatorStatus: {
            ...state.generatorStatus,
            running: data.running,
            pid: data.pid
          }
        }));
      }
    } catch (err) {
      console.error('Failed to fetch generator status:', err);
    }
  },

  fetchProfile: async () => {
    try {
      const res = await fetch('http://localhost:8000/api/settings/profile');
      if (res.ok) {
        const data = await res.json();
        set({ profile: data });
      }
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    }
  },

  fetchCobolStatus: async () => {
    try {
      const res = await fetch('http://localhost:8000/api/cobol/status');
      if (res.ok) {
        const data = await res.json();
        set({ cobolStatus: data });
      }
    } catch (err) {
      console.error('Failed to fetch COBOL status:', err);
    }
  },

  fetchRealTimeMetrics: async () => {
    try {
      const [sumRes, graphRes, ewsRes] = await Promise.all([
        fetch('http://localhost:8000/api/v1/dashboard/summary').then(r => r.json()).catch(() => ({})),
        fetch('http://localhost:8000/api/v1/graph/stats').then(r => r.json()).catch(() => ({})),
        fetch('http://localhost:8000/api/v1/mule/ews/alerts').then(r => r.json()).catch(() => [])
      ]);
      
      set({
        realTimeMetrics: {
          accounts: sumRes?.total_accounts ?? 0,
          transactions: sumRes?.total_transactions ?? 0,
          alerts: sumRes?.high_risk_count ?? 0,
          mules: sumRes?.mule_count ?? 0,
          ewsEvents: ewsRes?.length ?? 0,
          nodes: graphRes?.total_nodes ?? 0,
          edges: graphRes?.total_edges ?? 0
        }
      });
    } catch (err) {
      console.error('Failed to fetch real-time metrics:', err);
    }
  },

  saveProfile: async (name, email, avatarUrl) => {
    try {
      const res = await fetch('http://localhost:8000/api/settings/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, avatar_url: avatarUrl })
      });
      if (res.ok) {
        const data = await res.json();
        set({ profile: data });
      }
    } catch (err) {
      console.error('Failed to save profile:', err);
    }
  }
}));
