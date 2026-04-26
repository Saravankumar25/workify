import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';

export default function LogStream({ logs = [], status = 'idle', className }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLineColor = (line) => {
    if (line.startsWith('✓') || line.includes('success')) return 'text-[#22c55e]';
    if (line.startsWith('✗') || line.includes('error') || line.includes('fail')) return 'text-[#ef4444]';
    if (line.startsWith('⚠') || line.includes('warn')) return 'text-[#f59e0b]';
    return 'text-[#888888]';
  };

  return (
    <div
      className={clsx(
        'bg-[#0a0a0a] border border-[#222222] rounded-lg p-4 font-mono text-sm overflow-y-auto',
        className
      )}
      style={{ maxHeight: '400px' }}
    >
      {logs.length === 0 && status === 'idle' && (
        <p className="text-[#444444]">Waiting for logs...</p>
      )}
      {logs.map((line, i) => (
        <div key={i} className={clsx('py-0.5 leading-relaxed', getLineColor(line))}>
          <span className="text-[#444444] mr-3 select-none">{String(i + 1).padStart(3, '0')}</span>
          {line}
        </div>
      ))}
      {status === 'streaming' && (
        <div className="py-0.5 text-[#444444] animate-pulse">▌</div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
