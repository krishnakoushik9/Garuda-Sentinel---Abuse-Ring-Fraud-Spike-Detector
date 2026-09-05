import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnimatePresence } from 'framer-motion';
import { lazy, Suspense, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAppStore } from '@/stores/appStore';

// Lazy-loaded pages
const LandingPage = lazy(() => import('@/pages/LandingPage'));
const OverviewPage = lazy(() => import('@/pages/OverviewPage'));
const TransactionsPage = lazy(() => import('@/pages/TransactionsPage'));
const AccountsPage = lazy(() => import('@/pages/AccountsPage'));
const GraphPage = lazy(() => import('@/pages/GraphPage'));
const InvestigatePage = lazy(() => import('@/pages/InvestigatePage'));
const AlertsPage = lazy(() => import('@/pages/AlertsPage'));
const RegulatoryPage = lazy(() => import('@/pages/RegulatoryPage'));
const GovDataIntelligence = lazy(() => import('@/pages/GovDataIntelligence'));
const ChannelsPage = lazy(() => import('@/pages/ChannelsPage'));
const ModelsPage = lazy(() => import('@/pages/ModelsPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function Loading() {
  return (
    <div className="min-h-screen bg-void flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-600 animate-pulse" />
        <span className="text-xs text-white/40 tracking-[0.3em] uppercase">Loading Intelligence</span>
      </div>
    </div>
  );
}

export default function App() {
  const theme = useAppStore((state) => state.theme);

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  }, [theme]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AnimatePresence mode="wait">
          <Suspense fallback={<Loading />}>
            <Routes>
              {/* Landing */}
              <Route path="/" element={<LandingPage />} />

              {/* Dashboard */}
              <Route path="/dashboard" element={<DashboardLayout />}>
                <Route index element={<OverviewPage />} />
                <Route path="transactions" element={<TransactionsPage />} />
                <Route path="accounts" element={<AccountsPage />} />
                <Route path="graph" element={<GraphPage />} />
                <Route path="investigate" element={<InvestigatePage />} />
                <Route path="alerts" element={<AlertsPage />} />
                <Route path="intelligence" element={<GovDataIntelligence />} />
                <Route path="regulatory" element={<RegulatoryPage />} />
                <Route path="channels" element={<ChannelsPage />} />
                <Route path="models" element={<ModelsPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>

              <Route path="/intelligence" element={<Navigate to="/dashboard/intelligence" replace />} />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AnimatePresence>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
