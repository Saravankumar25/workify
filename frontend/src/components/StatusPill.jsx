import { clsx } from 'clsx';

const statusConfig = {
  planned: { label: 'Planned', bg: 'bg-[#1a1a1a]', text: 'text-[#888888]', dot: 'bg-[#888888]' },
  drafted: { label: 'Drafted', bg: 'bg-[#1a1a2e]', text: 'text-blue-400', dot: 'bg-blue-400' },
  submitted: { label: 'Submitted', bg: 'bg-[#0a1a0a]', text: 'text-[#22c55e]', dot: 'bg-[#22c55e]' },
  failed: { label: 'Failed', bg: 'bg-[#1a0a0a]', text: 'text-[#ef4444]', dot: 'bg-[#ef4444]' },
  needs_action: { label: 'Needs Action', bg: 'bg-[#1a1a0a]', text: 'text-[#f59e0b]', dot: 'bg-[#f59e0b]' },
};

export default function StatusPill({ status }) {
  const config = statusConfig[status] || statusConfig.planned;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
        config.bg,
        config.text
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', config.dot)} />
      {config.label}
    </span>
  );
}
