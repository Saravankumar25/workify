import { useNavigate } from 'react-router-dom';
import { MapPin, Building2, ExternalLink } from 'lucide-react';

export default function JobCard({ job }) {
  const navigate = useNavigate();

  return (
    <div className="glass-card p-5 hover:border-[#333333] transition-colors group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-base truncate group-hover:text-[#f5f5f5]">
            {job.title}
          </h3>
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
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#888888] hover:text-white transition-colors p-1"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={16} />
          </a>
        )}
      </div>

      {job.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {job.skills.slice(0, 5).map((skill) => (
            <span
              key={skill}
              className="text-xs px-2 py-0.5 rounded bg-[#1a1a1a] text-[#888888] border border-[#222222]"
            >
              {skill}
            </span>
          ))}
          {job.skills.length > 5 && (
            <span className="text-xs px-2 py-0.5 text-[#888888]">
              +{job.skills.length - 5}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate(`/jobs/${job.id}`)}
          className="text-xs px-3 py-1.5 rounded-md border border-[#222222] text-[#888888] hover:text-white hover:border-[#444444] transition-colors"
        >
          Details
        </button>
        <button
          onClick={() => navigate(`/compose/${job.id}`)}
          className="text-xs px-3 py-1.5 rounded-md bg-white text-black font-medium hover:bg-[#e5e5e5] transition-colors"
        >
          Compose →
        </button>
      </div>
    </div>
  );
}
