import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FileText, CheckCircle, Clock, XCircle, ArrowRight, Search, List } from 'lucide-react';
import api from '@/lib/api';
import useAuth from '@/store/useAuth';
import StatusPill from '@/components/StatusPill';

const statCards = [
  { key: 'total', label: 'Total Applied', icon: FileText, color: 'text-white', bg: '' },
  { key: 'submitted', label: 'Submitted', icon: CheckCircle, color: 'text-[#22c55e]', bg: 'bg-[#0a1a0a]' },
  { key: 'in_progress', label: 'In Progress', icon: Clock, color: 'text-[#f59e0b]', bg: 'bg-[#1a1a0a]' },
  { key: 'failed', label: 'Failed', icon: XCircle, color: 'text-[#ef4444]', bg: 'bg-[#1a0a0a]' },
];

function countByStatus(applications, status) {
  return applications.filter((a) => a.status === status).length;
}

function StatCardSkeleton() {
  return (
    <div className="glass-card p-5">
      <div className="animate-pulse">
        <div className="w-8 h-8 bg-[#111111] rounded mb-3" />
        <div className="w-16 h-8 bg-[#111111] rounded mb-2" />
        <div className="w-20 h-4 bg-[#111111] rounded" />
      </div>
    </div>
  );
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 animate-pulse">
      <div className="w-16 h-5 bg-[#111111] rounded-full" />
      <div className="w-40 h-4 bg-[#111111] rounded" />
      <div className="w-24 h-4 bg-[#111111] rounded ml-auto" />
    </div>
  );
}

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const user = useAuth((s) => s.user);

  const { data: applications, isLoading: appsLoading } = useQuery({
    queryKey: ['applications', { limit: 5 }],
    queryFn: () => api.get('/applications', { params: { limit: 5 } }).then((r) => r.data),
  });

  const { data: allApps, isLoading: allAppsLoading } = useQuery({
    queryKey: ['applications-all'],
    queryFn: () => api.get('/applications').then((r) => r.data),
  });

  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ['logs-runs', { limit: 5 }],
    queryFn: () => api.get('/logs/runs', { params: { limit: 5 } }).then((r) => r.data),
  });

  const appList = applications?.applications ?? [];
  const allAppList = allApps?.applications ?? [];
  const logList = logs?.runs ?? [];

  const stats = {
    total: allAppList.length,
    submitted: countByStatus(allAppList, 'submitted'),
    in_progress: countByStatus(allAppList, 'drafted') + countByStatus(allAppList, 'needs_action'),
    failed: countByStatus(allAppList, 'failed'),
  };

  const statsLoading = allAppsLoading;
  const displayName = user?.displayName || user?.email?.split('@')[0] || 'there';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-[#888888] mt-1">Welcome back, {displayName}</p>
      </div>

      {/* Stat Cards */}
      <motion.div
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
        variants={stagger}
        initial="hidden"
        animate="show"
      >
        {statsLoading
          ? statCards.map((c) => <StatCardSkeleton key={c.key} />)
          : statCards.map((card) => {
              const Icon = card.icon;
              return (
                <motion.div key={card.key} variants={fadeUp} className="glass-card p-5">
                  <Icon size={20} className={`${card.color} mb-3`} />
                  <p className="text-3xl font-bold text-white">{stats[card.key]}</p>
                  <p className="text-sm text-[#888888] mt-1">{card.label}</p>
                </motion.div>
              );
            })}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Applications */}
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Applications</h2>
            <button
              onClick={() => navigate('/applications')}
              className="text-xs text-[#888888] hover:text-white transition-colors flex items-center gap-1"
            >
              View all <ArrowRight size={12} />
            </button>
          </div>

          {appsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <RowSkeleton key={i} />
              ))}
            </div>
          ) : appList.length === 0 ? (
            <p className="text-[#888888] text-sm py-8 text-center">
              No applications yet. Start by searching for jobs.
            </p>
          ) : (
            <div className="divide-y divide-[#222222]">
              {appList.map((app) => (
                <button
                  key={app.id}
                  onClick={() => navigate('/applications')}
                  className="w-full flex items-center gap-3 py-3 px-2 hover:bg-[#111111] rounded-md transition-colors text-left"
                >
                  <StatusPill status={app.status} />
                  <span className="text-sm text-white truncate flex-1">{app.job_title || app.jobTitle || 'Untitled'}</span>
                  <span className="text-xs text-[#888888] shrink-0">{app.company || ''}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="glass-card p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/jobs')}
                className="w-full flex items-center gap-2 px-4 py-2.5 rounded-md bg-white text-black font-medium hover:bg-[#e5e5e5] transition-colors text-sm"
              >
                <Search size={16} />
                Search Jobs
              </button>
              <button
                onClick={() => navigate('/applications')}
                className="w-full flex items-center gap-2 px-4 py-2.5 rounded-md border border-[#222222] text-[#888888] hover:text-white hover:border-[#444444] transition-colors text-sm"
              >
                <List size={16} />
                View Tracker
              </button>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="glass-card p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
            {logsLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="w-full h-4 bg-[#111111] rounded" />
                  </div>
                ))}
              </div>
            ) : logList.length === 0 ? (
              <p className="text-[#888888] text-sm text-center py-4">No recent activity</p>
            ) : (
              <div className="space-y-2">
                {logList.map((log, i) => (
                  <div
                    key={log.id || i}
                    className="text-xs font-mono text-[#888888] py-1.5 border-b border-[#111111] last:border-0 truncate"
                  >
                    <span className="text-[#555555] mr-2">
                      {log.started_at
                        ? new Date(log.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : ''}
                    </span>
                    {log.kind || 'run'} — {log.success === true ? 'success' : log.success === false ? 'failed' : 'in progress'}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
