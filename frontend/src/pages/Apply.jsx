import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useSSE } from '@/lib/sse';
import api from '@/lib/api';
import LogStream from '@/components/LogStream';
import StatusPill from '@/components/StatusPill';
import { motion } from 'framer-motion';
import { Play, Loader2, CheckCircle, XCircle, AlertTriangle, ArrowRight } from 'lucide-react';

const STEPS = [
  { key: 'planned', label: 'Planned' },
  { key: 'drafted', label: 'Drafted' },
  { key: 'submitted', label: 'Submitted' },
];

function StepTimeline({ currentStatus }) {
  const stepIndex = STEPS.findIndex((s) => s.key === currentStatus);
  const activeIdx = stepIndex === -1 ? 0 : stepIndex;

  return (
    <div className="flex items-center gap-2">
      {STEPS.map((step, i) => {
        const isComplete = i < activeIdx;
        const isActive = i === activeIdx;
        return (
          <div key={step.key} className="flex items-center gap-2">
            {i > 0 && (
              <div
                className={`w-8 h-px ${isComplete ? 'bg-[#22c55e]' : 'bg-[#222222]'}`}
              />
            )}
            <div className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium border transition-colors ${
                  isComplete
                    ? 'bg-[#22c55e] border-[#22c55e] text-black'
                    : isActive
                    ? 'border-white text-white bg-[#111111]'
                    : 'border-[#333333] text-[#555555] bg-[#0a0a0a]'
                }`}
              >
                {isComplete ? '✓' : i + 1}
              </div>
              <span
                className={`text-xs font-medium ${
                  isComplete
                    ? 'text-[#22c55e]'
                    : isActive
                    ? 'text-white'
                    : 'text-[#555555]'
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CaptchaModal({ onResume, isResuming }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-6 max-w-md w-full mx-4"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#1a1a0a] flex items-center justify-center">
            <AlertTriangle size={20} className="text-[#f59e0b]" />
          </div>
          <div>
            <h3 className="text-white font-semibold">Captcha Detected</h3>
            <p className="text-sm text-[#888888]">
              LinkedIn is requesting a captcha verification.
            </p>
          </div>
        </div>
        <p className="text-sm text-[#888888] mb-6">
          Please open your browser, solve the captcha on LinkedIn, then click
          the button below to resume the apply process.
        </p>
        <button
          onClick={onResume}
          disabled={isResuming}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-white text-black font-medium hover:bg-[#e5e5e5] transition-colors text-sm disabled:opacity-50"
        >
          {isResuming ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Resuming...
            </>
          ) : (
            'Resume After Solving'
          )}
        </button>
      </motion.div>
    </div>
  );
}

export default function Apply() {
  const { applicationId } = useParams();
  const navigate = useNavigate();
  const [runId, setRunId] = useState(null);

  const { data: application, isLoading: appLoading } = useQuery({
    queryKey: ['application', applicationId],
    queryFn: () => api.get(`/applications/${applicationId}`).then((r) => r.data),
    enabled: !!applicationId,
  });

  const jobId = application?.job_id;
  const { data: job } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.get(`/jobs/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
  });

  const { logs, status: sseStatus } = useSSE(runId);

  const runMutation = useMutation({
    mutationFn: () =>
      api.post('/apply/run', { application_id: applicationId }).then((r) => r.data),
    onSuccess: (data) => setRunId(data.run_id),
  });

  const resumeMutation = useMutation({
    mutationFn: () =>
      api.post('/apply/resume', { run_id: runId }).then((r) => r.data),
  });

  const isRunning = sseStatus === 'streaming';
  const isDone = sseStatus === 'done';
  const isError = sseStatus === 'error';
  const isCaptcha = sseStatus === 'captcha';
  const isIdle = sseStatus === 'idle' && !runMutation.isPending;

  const currentStatus =
    isDone
      ? 'submitted'
      : isError
      ? 'failed'
      : isCaptcha
      ? 'needs_action'
      : application?.status || 'planned';

  if (appLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-3">
          <div className="w-64 h-7 bg-[#111111] rounded" />
          <div className="w-40 h-5 bg-[#111111] rounded" />
        </div>
        <div className="animate-pulse w-full h-64 bg-[#0a0a0a] rounded-lg border border-[#222222]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-white">
              {job?.title || application?.job_title || 'Apply'}
            </h1>
            <StatusPill status={currentStatus} />
          </div>
          <p className="text-[#888888] text-sm">
            {job?.company || application?.company || ''}
            {(job?.location || application?.location) &&
              ` · ${job?.location || application?.location}`}
          </p>
        </div>
      </div>

      {/* Step Timeline */}
      <div className="glass-card p-4">
        <StepTimeline currentStatus={currentStatus} />
      </div>

      {/* Status Banners */}
      {isDone && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 rounded-lg bg-[#0a1a0a] border border-[#22c55e]/20"
        >
          <CheckCircle size={20} className="text-[#22c55e] shrink-0" />
          <div className="flex-1">
            <p className="text-[#22c55e] font-medium text-sm">
              Application submitted successfully
            </p>
            <p className="text-[#888888] text-xs mt-0.5">
              Your application has been delivered to the employer.
            </p>
          </div>
          <Link
            to="/applications"
            className="flex items-center gap-1.5 text-xs text-white bg-[#22c55e]/10 hover:bg-[#22c55e]/20 px-3 py-1.5 rounded-md transition-colors"
          >
            View in Tracker <ArrowRight size={12} />
          </Link>
        </motion.div>
      )}

      {isError && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 rounded-lg bg-[#1a0a0a] border border-[#ef4444]/20"
        >
          <XCircle size={20} className="text-[#ef4444] shrink-0" />
          <div className="flex-1">
            <p className="text-[#ef4444] font-medium text-sm">
              Apply run failed
            </p>
            <p className="text-[#888888] text-xs mt-0.5">
              An error occurred during the automation. You can retry.
            </p>
          </div>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-1.5 text-xs text-white bg-[#ef4444]/10 hover:bg-[#ef4444]/20 px-3 py-1.5 rounded-md transition-colors"
          >
            Retry
          </button>
        </motion.div>
      )}

      {isCaptcha && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 rounded-lg bg-[#1a1a0a] border border-[#f59e0b]/20"
        >
          <AlertTriangle size={20} className="text-[#f59e0b] shrink-0" />
          <div className="flex-1">
            <p className="text-[#f59e0b] font-medium text-sm">
              Captcha detected — action required
            </p>
            <p className="text-[#888888] text-xs mt-0.5">
              Solve the captcha in your browser, then resume.
            </p>
          </div>
        </motion.div>
      )}

      {/* Terminal Log Panel */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-medium text-[#888888]">Run Output</h2>
          {isRunning && (
            <span className="flex items-center gap-1.5 text-xs text-[#22c55e]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] animate-pulse" />
              Live
            </span>
          )}
        </div>
        <LogStream logs={logs} status={sseStatus} className="min-h-[300px]" />
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3">
        {isIdle && (
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-white text-black font-medium hover:bg-[#e5e5e5] transition-colors text-sm disabled:opacity-50"
          >
            {runMutation.isPending ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Apply
              </>
            )}
          </button>
        )}

        {isRunning && (
          <div className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-[#111111] border border-[#222222] text-[#888888] text-sm">
            <Loader2 size={16} className="animate-spin" />
            Running...
          </div>
        )}

        {isDone && (
          <button
            onClick={() => navigate('/applications')}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-white text-black font-medium hover:bg-[#e5e5e5] transition-colors text-sm"
          >
            View in Tracker <ArrowRight size={16} />
          </button>
        )}

        {isError && (
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 rounded-md border border-[#222222] text-white hover:border-[#444444] transition-colors text-sm"
          >
            {runMutation.isPending ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Retrying...
              </>
            ) : (
              <>
                <Play size={16} />
                Retry
              </>
            )}
          </button>
        )}

        {!isDone && !isError && !isIdle && !isRunning && !isCaptcha && null}
      </div>

      {/* Captcha Modal */}
      {isCaptcha && (
        <CaptchaModal
          onResume={() => resumeMutation.mutate()}
          isResuming={resumeMutation.isPending}
        />
      )}

      {/* Rate limit error feedback */}
      {runMutation.isError && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-[#ef4444] mt-2"
        >
          {runMutation.error?.response?.data?.detail || 'Failed to start apply run. Please try again.'}
        </motion.div>
      )}
    </div>
  );
}
