import { Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import { TopNav } from './TopNav';

export function DashboardLayout() {
  return (
    <div className="min-h-screen bg-void">
      <TopNav />
      <motion.main
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="pt-20 px-4 lg:px-8 pb-8 max-w-[1600px] mx-auto"
      >
        <Outlet />
      </motion.main>
    </div>
  );
}
