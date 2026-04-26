import { useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import api from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal,
  Filter,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
} from 'lucide-react';

const KINDS = ['All', 'Scrape', 'Compose', 'Apply'];

const kindColors = {
  scrape: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  compose: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  apply: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
};

const PAGE_SIZE = 20;

function formatDuration(ms) {
  if (ms == null) return '—';
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

function formatTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function KindBadge({ kind }) {
  const key = kind?.toLowerCase() || '';
  const color = kindColors[key] || 'bg-[#111111] text-[#888888] border-[#222222]';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${color}`}
    >
      {kind || 'unknown'}
    </span>
  );
}

function LogViewer({ runId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['log-run', runId],
    queryFn: () => api.get(`/logs/runs/${runId}`).then((r) => r.data),
    enabled: !!runId,
  });

  const lines = data?.log_lines || [];

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden"
    >
      <div className="bg-[#050505] border-t border-[#222222] p-4 max-h-80 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center gap-2 py-4 justify-center">
            <Loader2 size={16} className="animate-spin text-[#888888]" />
            <span className="text-sm text-[#888888]">Loading logs...</span>
          </div>
        ) : lines.length === 0 ? (
          <p className="text-sm text-[#555555] text-center py-4">No log output</p>
        ) : (
          <pre className="font-mono text-xs text-[#cccccc] whitespace-pre-wrap leading-relaxed">
            {lines.map((line, i) => (
              <div
                key={i}
                className="hover:bg-[#111111] px-1 -mx-1 rounded"
              >
                <span className="text-[#444444] select-none mr-3 inline-block w-8 text-right">
                  {i + 1}
                </span>
                {line}
              </div>
            ))}
          </pre>
        )}
      </div>
    </motion.div>
  );
}

function RowSkeleton() {
  return (
    <div className="flex items-center gap-4 px-4 py-3 animate-pulse">
      <div className="w-16 h-5 bg-[#111111] rounded" />
      <div className="w-6 h-5 bg-[#111111] rounded" />
      <div className="w-32 h-4 bg-[#111111] rounded" />
      <div className="w-16 h-4 bg-[#111111] rounded ml-auto" />
    </div>
  );
}

export default function Logs() {
  const [kindFilter, setKindFilter] = useState('All');
  const [successFilter, setSuccessFilter] = useState(null);
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState(null);

  const params = {
    limit: PAGE_SIZE,
    skip: page * PAGE_SIZE,
  };
  if (kindFilter !== 'All') params.kind = kindFilter.toLowerCase();
  if (successFilter !== null) params.success = successFilter;

  const { data, isLoading } = useQuery({
    queryKey: ['logs-runs', params],
    queryFn: () => api.get('/logs/runs', { params }).then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  const runs = data?.runs ?? [];
  const hasMore = runs.length === PAGE_SIZE;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Logs</h1>
        <p className="text-[#888888] mt-1">Run history and execution logs</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Filter size={14} className="text-[#888888]" />
          <span className="text-xs text-[#888888] uppercase tracking-wider">Kind</span>
        </div>
        <div className="flex gap-1">
          {KINDS.map((kind) => (
            <button
              key={kind}
              onClick={() => {
                setKindFilter(kind);
                setPage(0);
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                kindFilter === kind
                  ? 'bg-white text-black'
                  : 'bg-[#111111] text-[#888888] hover:text-white border border-[#222222]'
              }`}
            >
              {kind}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-[#222222]" />

        <div className="flex gap-1">
          {[
            { label: 'All', value: null },
            { label: 'Success', value: true },
            { label: 'Failed', value: false },
          ].map((opt) => (
            <button
              key={opt.label}
              onClick={() => {
                setSuccessFilter(opt.value);
                setPage(0);
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                successFilter === opt.value
                  ? 'bg-white text-black'
                  : 'bg-[#111111] text-[#888888] hover:text-white border border-[#222222]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[auto_80px_80px_1fr_100px_48px] gap-2 px-4 py-2.5 border-b border-[#222222] text-xs font-medium text-[#888888] uppercase tracking-wider">
          <div className="w-5" />
          <div>Kind</div>
          <div>Status</div>
          <div>Started At</div>
          <div>Duration</div>
          <div />
        </div>

        {/* Rows */}
        {isLoading ? (
          <div>
            {Array.from({ length: 8 }).map((_, i) => (
              <RowSkeleton key={i} />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-2">
            <Terminal size={28} className="text-[#333333]" />
            <p className="text-sm text-[#888888]">No runs found</p>
          </div>
        ) : (
          <div className="divide-y divide-[#222222]">
            {runs.map((run) => {
              const isExpanded = expandedId === run.id;
              return (
                <div key={run.id}>
                  <button
                    onClick={() =>
                      setExpandedId(isExpanded ? null : run.id)
                    }
                    className="w-full grid grid-cols-[auto_80px_80px_1fr_100px_48px] gap-2 items-center px-4 py-3 text-left hover:bg-[#0a0a0a] transition-colors"
                  >
                    <div className="w-5 flex items-center justify-center text-[#555555]">
                      {isExpanded ? (
                        <ChevronDown size={14} />
                      ) : (
                        <ChevronRight size={14} />
                      )}
                    </div>
                    <KindBadge kind={run.kind} />
                    <div>
                      {run.success ? (
                        <CheckCircle size={16} className="text-[#22c55e]" />
                      ) : run.success === false ? (
                        <XCircle size={16} className="text-[#ef4444]" />
                      ) : (
                        <Clock size={16} className="text-[#f59e0b]" />
                      )}
                    </div>
                    <span className="text-sm text-[#cccccc] truncate">
                      {formatTime(run.started_at || run.created_at)}
                    </span>
                    <span className="text-sm text-[#888888] font-mono">
                      {formatDuration(run.duration_ms)}
                    </span>
                    <div />
                  </button>

                  <AnimatePresence>
                    {isExpanded && <LogViewer runId={run.id} />}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {(page > 0 || hasMore) && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-4 py-2 border border-[#222222] text-[#888888] rounded-md text-sm hover:text-white hover:border-[#444444] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-xs text-[#555555]">Page {page + 1}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="px-4 py-2 border border-[#222222] text-[#888888] rounded-md text-sm hover:text-white hover:border-[#444444] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
