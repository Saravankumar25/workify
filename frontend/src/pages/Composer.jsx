import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import MarkdownEditor from '@/components/MarkdownEditor';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Loader2,
  FileText,
  Mail,
  MessageSquare,
  Download,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

const TABS = [
  { key: 'resume', label: 'Resume', icon: FileText },
  { key: 'cover_letter', label: 'Cover Letter', icon: Mail },
  { key: 'qa', label: 'Q&A', icon: MessageSquare },
];

export default function Composer() {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('resume');
  const [resumeMd, setResumeMd] = useState('');
  const [coverLetterMd, setCoverLetterMd] = useState('');
  const [qa, setQa] = useState([]);
  const [applicationId, setApplicationId] = useState(null);
  const [keywordCoverage, setKeywordCoverage] = useState(null);

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.get(`/jobs/${jobId}`).then((r) => r.data),
  });

  const generate = useMutation({
    mutationFn: () =>
      api.post('/compose/generate', { job_id: jobId }).then((r) => r.data),
    onSuccess: (data) => {
      setResumeMd(data.resume_md || '');
      setCoverLetterMd(data.cover_letter_md || '');
      setQa(data.qa || []);
      if (data.application_id) setApplicationId(data.application_id);
      if (data.keyword_coverage != null) setKeywordCoverage(data.keyword_coverage);
    },
  });

  const exportPdf = useMutation({
    mutationFn: () =>
      api.post('/compose/export', {
        application_id: applicationId,
        resume_md: resumeMd,
        cover_letter_md: coverLetterMd,
      }, { responseType: 'blob' }),
    onSuccess: (res) => {
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workify-${jobId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const hasGenerated = !!(resumeMd || coverLetterMd || qa.length);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="min-w-0">
          {jobLoading ? (
            <div className="space-y-2">
              <div className="h-6 w-64 bg-[#111111] rounded animate-pulse" />
              <div className="h-4 w-40 bg-[#111111] rounded animate-pulse" />
            </div>
          ) : job ? (
            <>
              <h1 className="text-xl font-bold text-white truncate">{job.title}</h1>
              <p className="text-sm text-[#888888]">{job.company}</p>
            </>
          ) : (
            <h1 className="text-xl font-bold text-white">Composer</h1>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {!hasGenerated ? (
            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-white text-black text-sm font-medium hover:bg-[#e5e5e5] transition-colors disabled:opacity-50"
            >
              <Sparkles size={16} />
              Generate
            </button>
          ) : (
            <>
              <button
                onClick={() => exportPdf.mutate()}
                disabled={exportPdf.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-[#222222] text-sm text-[#888888] hover:text-white hover:border-[#444444] transition-colors disabled:opacity-50"
              >
                <Download size={16} />
                {exportPdf.isPending ? 'Exporting…' : 'Export PDF'}
              </button>
              {applicationId && (
                <button
                  onClick={() => navigate(`/apply/${applicationId}`)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-white text-black text-sm font-medium hover:bg-[#e5e5e5] transition-colors"
                >
                  Use for Apply
                  <ArrowRight size={16} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Split layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Job description */}
        <div className="glass-card p-5 overflow-y-auto max-h-[calc(100vh-220px)]">
          <h2 className="text-sm font-medium text-[#888888] uppercase tracking-wider mb-4">
            Job Description
          </h2>
          <div className="prose-workify">
            {jobLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-4 bg-[#111111] rounded animate-pulse"
                    style={{ width: `${70 + Math.random() * 30}%` }}
                  />
                ))}
              </div>
            ) : job?.description ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {job.description}
              </ReactMarkdown>
            ) : (
              <p className="text-[#888888] italic">No description available.</p>
            )}
          </div>
        </div>

        {/* Right: Tabbed editor */}
        <div className="space-y-4">
          {/* Tab bar */}
          <div className="flex border-b border-[#222222]">
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium transition-colors relative ${
                  activeTab === key
                    ? 'text-white'
                    : 'text-[#888888] hover:text-white'
                }`}
              >
                <Icon size={14} />
                {label}
                {activeTab === key && (
                  <motion.div
                    layoutId="composer-tab-indicator"
                    className="absolute bottom-0 left-0 right-0 h-px bg-white"
                  />
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="min-h-[400px]">
            {activeTab === 'resume' && (
              <MarkdownEditor
                value={resumeMd}
                onChange={setResumeMd}
                placeholder="Generate or write your tailored resume…"
              />
            )}

            {activeTab === 'cover_letter' && (
              <MarkdownEditor
                value={coverLetterMd}
                onChange={setCoverLetterMd}
                placeholder="Generate or write your cover letter…"
              />
            )}

            {activeTab === 'qa' && (
              <div className="space-y-3">
                {qa.length > 0 ? (
                  qa.map((item, i) => (
                    <div key={i} className="glass-card p-4 space-y-2">
                      <p className="text-sm font-medium text-white">{item.question}</p>
                      <p className="text-sm text-[#cccccc] leading-relaxed">
                        {item.answer}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="glass-card p-8 text-center">
                    <MessageSquare size={32} className="text-[#333333] mx-auto mb-3" />
                    <p className="text-sm text-[#888888]">
                      Q&A pairs will appear here after generation.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Keyword coverage */}
          {keywordCoverage != null && (
            <div className="glass-card p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-[#888888] uppercase tracking-wider">
                  Keyword Coverage
                </p>
                <span className="text-xs text-white font-medium">
                  {Math.round(keywordCoverage * 100)}%
                </span>
              </div>
              <div className="h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${keywordCoverage * 100}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  className="h-full bg-white rounded-full"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Generation overlay */}
      <AnimatePresence>
        {generate.isPending && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          >
            <div className="flex flex-col items-center gap-4">
              <Loader2 size={36} className="text-white animate-spin" />
              <p className="text-sm text-[#888888]">Generating tailored content…</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
