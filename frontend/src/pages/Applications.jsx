import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import StatusPill from '@/components/StatusPill';
import { motion } from 'framer-motion';
import { LayoutGrid, List, Search, Trash2, Eye, Loader2 } from 'lucide-react';

const STATUS_COLUMNS = [
  { key: 'planned', label: 'Planned' },
  { key: 'drafted', label: 'Drafted' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'needs_action', label: 'Needs Action' },
  { key: 'failed', label: 'Failed' },
];

const FILTER_CHIPS = [
  { key: 'all', label: 'All' },
  ...STATUS_COLUMNS,
];

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};

function KanbanCard({ app, onClick }) {
  return (
    <motion.button
      variants={fadeUp}
      onClick={onClick}
      className="w-full text-left glass-card p-4 hover:border-[#333333] transition-colors group"
    >
      <h4 className="text-sm font-medium text-white truncate group-hover:text-[#f5f5f5]">
        {app.job_title || app.jobTitle || 'Untitled'}
      </h4>
      <p className="text-xs text-[#888888] mt-1 truncate">
        {app.company || 'Unknown company'}
      </p>
      <div className="flex items-center justify-between mt-3">
        <StatusPill status={app.status} />
        <span className="text-[10px] text-[#555555]">
          {app.created_at
            ? new Date(app.created_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              })
            : ''}
        </span>
      </div>
    </motion.button>
  );
}

function KanbanColumn({ column, apps, onCardClick }) {
  return (
    <div className="flex-1 min-w-[220px]">
      <div className="flex items-center gap-2 mb-3 px-1">
        <h3 className="text-xs font-semibold text-[#888888] uppercase tracking-wider">
          {column.label}
        </h3>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#1a1a1a] text-[#888888] border border-[#222222]">
          {apps.length}
        </span>
      </div>
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="glass-card p-2 space-y-2 min-h-[300px] max-h-[calc(100vh-320px)] overflow-y-auto"
      >
        {apps.length === 0 ? (
          <p className="text-xs text-[#444444] text-center py-8">
            No applications
          </p>
        ) : (
          apps.map((app) => (
            <KanbanCard
              key={app.id}
              app={app}
              onClick={() => onCardClick(app.id)}
            />
          ))
        )}
      </motion.div>
    </div>
  );
}

function TableView({ apps, onRowClick, onDelete, isDeleting }) {
  const [sortField, setSortField] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sorted = [...apps].sort((a, b) => {
    let aVal = a[sortField] || '';
    let bVal = b[sortField] || '';
    if (sortField === 'created_at') {
      aVal = new Date(aVal).getTime() || 0;
      bVal = new Date(bVal).getTime() || 0;
    }
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const SortHeader = ({ field, children }) => (
    <button
      onClick={() => toggleSort(field)}
      className="flex items-center gap-1 text-xs font-semibold text-[#888888] uppercase tracking-wider hover:text-white transition-colors"
    >
      {children}
      {sortField === field && (
        <span className="text-[10px]">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </button>
  );

  return (
    <div className="glass-card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[#222222]">
            <th className="text-left px-4 py-3">
              <SortHeader field="job_title">Job Title</SortHeader>
            </th>
            <th className="text-left px-4 py-3">
              <SortHeader field="company">Company</SortHeader>
            </th>
            <th className="text-left px-4 py-3">
              <SortHeader field="status">Status</SortHeader>
            </th>
            <th className="text-left px-4 py-3">
              <SortHeader field="created_at">Created</SortHeader>
            </th>
            <th className="text-right px-4 py-3">
              <span className="text-xs font-semibold text-[#888888] uppercase tracking-wider">
                Actions
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center py-12 text-[#888888] text-sm">
                No applications found
              </td>
            </tr>
          ) : (
            sorted.map((app) => (
              <tr
                key={app.id}
                onClick={() => onRowClick(app.id)}
                className="border-b border-[#222222] last:border-0 hover:bg-[#111111] cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <span className="text-sm text-white">
                    {app.job_title || app.jobTitle || 'Untitled'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-[#888888]">
                    {app.company || '—'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <StatusPill status={app.status} />
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-[#888888]">
                    {app.created_at
                      ? new Date(app.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })
                      : '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div
                    className="flex items-center justify-end gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => onRowClick(app.id)}
                      className="p-1.5 rounded-md text-[#888888] hover:text-white hover:bg-[#1a1a1a] transition-colors"
                      title="View"
                    >
                      <Eye size={15} />
                    </button>
                    <button
                      onClick={() => onDelete(app.id)}
                      disabled={isDeleting}
                      className="p-1.5 rounded-md text-[#888888] hover:text-[#ef4444] hover:bg-[#1a0a0a] transition-colors disabled:opacity-50"
                      title="Delete"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function Applications() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [view, setView] = useState('kanban');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const { data, isLoading } = useQuery({
    queryKey: ['applications', { status: statusFilter === 'all' ? undefined : statusFilter, search: search || undefined }],
    queryFn: () =>
      api
        .get('/applications', {
          params: {
            ...(statusFilter !== 'all' && { status: statusFilter }),
            ...(search && { search }),
          },
        })
        .then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/applications/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['applications'] }),
  });

  const apps = data?.applications ?? [];

  const handleCardClick = (id) => navigate(`/apply/${id}`);
  const handleDelete = (id) => {
    if (window.confirm('Delete this application?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Applications</h1>
          <p className="text-[#888888] text-sm mt-1">
            Track and manage your job applications
          </p>
        </div>
        <div className="flex items-center gap-1 p-1 rounded-lg bg-[#0a0a0a] border border-[#222222]">
          <button
            onClick={() => setView('kanban')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              view === 'kanban'
                ? 'bg-[#1a1a1a] text-white'
                : 'text-[#888888] hover:text-white'
            }`}
          >
            <LayoutGrid size={14} />
            Kanban
          </button>
          <button
            onClick={() => setView('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              view === 'table'
                ? 'bg-[#1a1a1a] text-white'
                : 'text-[#888888] hover:text-white'
            }`}
          >
            <List size={14} />
            Table
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555555]"
          />
          <input
            type="text"
            placeholder="Search by title or company..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-md bg-[#0a0a0a] border border-[#222222] text-sm text-white placeholder-[#555555] focus:outline-none focus:border-[#444444] transition-colors"
          />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.key}
              onClick={() => setStatusFilter(chip.key)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors border ${
                statusFilter === chip.key
                  ? 'bg-white text-black border-white'
                  : 'bg-transparent text-[#888888] border-[#222222] hover:text-white hover:border-[#444444]'
              }`}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-[#888888]" />
        </div>
      ) : view === 'kanban' ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STATUS_COLUMNS.map((col) => {
            const colApps = apps.filter((a) => a.status === col.key);
            return (
              <KanbanColumn
                key={col.key}
                column={col}
                apps={colApps}
                onCardClick={handleCardClick}
              />
            );
          })}
        </div>
      ) : (
        <TableView
          apps={apps}
          onRowClick={handleCardClick}
          onDelete={handleDelete}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
