import { useEffect, useRef, useState } from 'react';
import { auth } from '@/firebase';

/**
 * @param {string|null} runId
 * @returns {{ logs: string[], status: string }}
 */
export function useSSE(runId) {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('idle');
  const esRef = useRef(null);

  useEffect(() => {
    if (!runId) return;

    async function connect() {
      const token = await auth.currentUser?.getIdToken();
      const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/apply/stream/${runId}?token=${token}`;
      const es = new EventSource(url);
      esRef.current = es;
      setStatus('streaming');

      es.onmessage = (e) => {
        const line = e.data;
        if (line === '__PING__') return;
        if (line.startsWith('__DONE__')) { setStatus('done'); es.close(); return; }
        if (line.startsWith('__ERROR__')) { setStatus('error'); es.close(); return; }
        if (line.startsWith('__CAPTCHA_DETECTED__')) { setStatus('captcha'); es.close(); return; }
        setLogs((prev) => [...prev, line]);
      };

      es.onerror = () => {
        setStatus('error');
        es.close();
      };
    }

    connect();
    return () => esRef.current?.close();
  }, [runId]);

  return { logs, status };
}
