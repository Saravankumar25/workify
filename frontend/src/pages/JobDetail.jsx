import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowLeft,
  Building2,
  MapPin,
  DollarSign,
  ExternalLink,
  Briefcase,
} from 'lucide-react';

function SkeletonBlock({ className }) {
  return (
    <div className={`bg-[#111111] rounded animate-pulse ${className}`} />
  );
}

function JobDetailSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonBlock className="h-5 w-32" />
      <div className="space-y-2">
        <SkeletonBlock className="h-8 w-80" />
        <SkeletonBlock className="h-4 w-48" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <SkeletonBlock className="h-4 w-full" />
          <SkeletonBlock className="h-4 w-full" />
          <SkeletonBlock className="h-4 w-5/6" />
          <SkeletonBlock className="h-4 w-full" />
          <SkeletonBlock className="h-4 w-4/6" />
          <SkeletonBlock className="h-4 w-full" />
          <SkeletonBlock className="h-4 w-3/4" />
        </div>
        <div className="space-y-4">
          <SkeletonBlock className="h-64 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export default function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ['job', id],
    queryFn: () => api.get(`/jobs/${id}`).then((r) => r.data),
  });

  if (isLoading) {
    return <JobDetailSkeleton />;
  }

  if (isError || !job) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Briefcase size={48} className="text-[#333333] mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">Job not found</h2>
        <p className="text-[#888888] mb-6">
          This job may have been removed or the link is invalid.
        </p>
        <Link
          to="/jobs"
          className="inline-flex items-center gap-2 text-sm text-[#888888] hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Jobs
        </Link>
      </div>
    );
  }

  const hasSalary = job.min_salary || job.max_salary;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="space-y-6"
    >
      <Link
        to="/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-[#888888] hover:text-white transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Jobs
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-white">{job.title}</h1>
        <div className="flex items-center gap-3 mt-1.5 text-[#888888] text-sm">
          <span className="flex items-center gap-1">
            <Building2 size={14} />
            {job.company}
          </span>
          {job.location && (
            <span className="flex items-center gap-1">
              <MapPin size={14} />
              {job.location}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Job description */}
        <div className="lg:col-span-2">
          <div className="glass-card p-6">
            <div className="prose-workify">
              {job.description ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {job.description}
                </ReactMarkdown>
              ) : (
                <p className="text-[#888888] italic">No description available.</p>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          <div className="glass-card p-5 space-y-5">
            <div>
              <p className="text-xs text-[#888888] uppercase tracking-wider mb-1">Company</p>
              <p className="text-white text-sm font-medium flex items-center gap-1.5">
                <Building2 size={14} className="text-[#888888]" />
                {job.company}
              </p>
            </div>

            {job.location && (
              <div>
                <p className="text-xs text-[#888888] uppercase tracking-wider mb-1">Location</p>
                <p className="text-white text-sm font-medium flex items-center gap-1.5">
                  <MapPin size={14} className="text-[#888888]" />
                  {job.location}
                </p>
              </div>
            )}

            {hasSalary && (
              <div>
                <p className="text-xs text-[#888888] uppercase tracking-wider mb-1">Salary</p>
                <p className="text-white text-sm font-medium flex items-center gap-1.5">
                  <DollarSign size={14} className="text-[#888888]" />
                  {job.min_salary && job.max_salary
                    ? `$${job.min_salary.toLocaleString()} – $${job.max_salary.toLocaleString()}`
                    : job.min_salary
                      ? `From $${job.min_salary.toLocaleString()}`
                      : `Up to $${job.max_salary.toLocaleString()}`}
                  {job.currency && (
                    <span className="text-[#888888] text-xs ml-1">{job.currency}</span>
                  )}
                </p>
              </div>
            )}

            {job.skills?.length > 0 && (
              <div>
                <p className="text-xs text-[#888888] uppercase tracking-wider mb-2">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {job.skills.map((skill) => (
                    <span
                      key={skill}
                      className="text-xs px-2 py-0.5 rounded bg-[#1a1a1a] text-[#888888] border border-[#222222]"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {job.url && (
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full px-4 py-2 rounded-md border border-[#222222] text-sm text-[#888888] hover:text-white hover:border-[#444444] transition-colors"
              >
                <ExternalLink size={14} />
                View on LinkedIn
              </a>
            )}
          </div>

          <button
            onClick={() => navigate(`/compose/${job.id}`)}
            className="w-full px-4 py-2.5 rounded-md bg-white text-black text-sm font-medium hover:bg-[#e5e5e5] transition-colors"
          >
            Start Composing →
          </button>
        </div>
      </div>
    </motion.div>
  );
}
