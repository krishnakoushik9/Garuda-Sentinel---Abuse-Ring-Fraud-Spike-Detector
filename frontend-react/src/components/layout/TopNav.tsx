import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  ArrowRightLeft,
  Users,
  GitBranch,
  Search,
  Bell,
  Database,
  Scale,
  Radio,
  Cpu,
  Settings,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

const navItems = [
  { path: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { path: '/dashboard/transactions', label: 'Transactions', icon: ArrowRightLeft },
  { path: '/dashboard/accounts', label: 'Accounts', icon: Users },
  { path: '/dashboard/graph', label: 'Graph', icon: GitBranch },
  { path: '/dashboard/investigate', label: 'Investigate', icon: Search },
  { path: '/dashboard/alerts', label: 'Alerts', icon: Bell },
  { path: '/dashboard/intelligence', label: 'Live Intelligence', icon: Database },
  { path: '/dashboard/regulatory', label: 'Regulatory', icon: Scale },
  { path: '/dashboard/channels', label: 'Channels', icon: Radio },
  { path: '/dashboard/models', label: 'Models', icon: Cpu },
  { path: '/dashboard/settings', label: 'Settings', icon: Settings },
];

export function TopNav() {
  const location = useLocation();

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-7xl"
    >
      <div className="glass-strong rounded-2xl px-4 py-2 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/dashboard" className="flex items-center gap-3 px-3 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center">
            <span className="text-white font-bold text-xs">FI</span>
          </div>
          <span className="text-sm font-bold text-white tracking-wide hidden md:inline">
            FRAUD INTELLIGENCE
          </span>
        </NavLink>

        {/* Nav items */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className="relative"
              >
                <div
                  title={item.label}
                  className={`
                    flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-200
                    ${isActive ? 'text-cyan-400' : 'text-white/50 hover:text-white/80 hover:bg-white/5'}
                  `}
                >
                  <item.icon size={16} />
                </div>
                {isActive && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute inset-0 rounded-lg bg-cyan-500/10 border border-cyan-500/20"
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
              </NavLink>
            );
          })}
        </div>

        {/* System status */}
        <div className="flex items-center gap-3 shrink-0 pl-3">
          <Badge variant="green" size="sm" pulse>COBOL</Badge>
          <Badge variant="green" size="sm" pulse>ENGINE</Badge>
          <Badge variant="amber" size="sm">KAFKA</Badge>
        </div>
      </div>
    </motion.nav>
  );
}
