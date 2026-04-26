import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Search, MapPin, Loader2, Briefcase } from 'lucide-react';
import api from '@/lib/api';
import JobCard from '@/components/JobCard';

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

function CardSkeleton() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="w-3/4 h-5 bg-[#111111] rounded mb-3" />
      <div className="flex gap-3 mb-4">
        <div className="w-24 h-4 bg-[#111111] rounded" />
        <div className="w-20 h-4 bg-[#111111] rounded" />
      </div>
      <div className="flex gap-2 mb-4">
        <div className="w-14 h-5 bg-[#111111] rounded" />
        <div className="w-14 h-5 bg-[#111111] rounded" />
        <div className="w-14 h-5 bg-[#111111] rounded" />
      </div>
      <div className="flex gap-2">
        <div className="w-16 h-7 bg-[#111111] rounded-md" />
        <div className="w-20 h-7 bg-[#111111] rounded-md" />
      </div>
    </div>
  );
}

export default function JobsSearch() {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  const searchMutation = useMutation({
    mutationFn: (params) =>
      api.post('/jobs/search', { query: params.query, location: params.location, limit: 20 }).then((r) => r.data),
  });

  const { data: savedJobsRaw, isLoading: savedLoading } = useQuery({
    queryKey: ['jobs', page],
    queryFn: () =>
      api.get('/jobs', { params: { skip: (page - 1) * pageSize, limit: pageSize } }).then((r) => r.data),
  });

  const savedJobs = savedJobsRaw?.jobs ?? [];
  const totalPages = Math.ceil((savedJobsRaw?.total ?? savedJobs.length) / pageSize) || 1;

  const searchResults = searchMutation.data?.jobs ?? [];

  function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate({ query: query.trim(), location: location.trim() });
  }

  const showSearchResults = searchMutation.isSuccess || searchMutation.isPending;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Job Search</h1>
        <p className="text-[#888888] mt-1">Find and save jobs to apply</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555555]" />
          <input
            type="text"
            placeholder="Job title, keywords..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#0a0a0a] border border-[#222222] rounded-md py-2.5 pl-9 pr-3 text-sm text-white placeholder:text-[#555555] focus:outline-none focus:border-[#444444] transition-colors"
          />
        </div>
        <div className="relative sm:w-48">
          <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#555555]" />
          <input
            type="text"
            placeholder="Location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full bg-[#0a0a0a] border border-[#222222] rounded-md py-2.5 pl-9 pr-3 text-sm text-white placeholder:text-[#555555] focus:outline-none focus:border-[#444444] transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={searchMutation.isPending || !query.trim()}
          className="px-6 py-2.5 bg-white text-black rounded-md font-medium text-sm hover:bg-[#e5e5e5] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {searchMutation.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Search size={16} />
          )}
          Search
        </button>
      </form>

      {/* Search Results */}
      {showSearchResults && (
        <section>
          <h2 className="text-lg font-semibold text-white mb-4">Search Results</h2>

          {searchMutation.isPending ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <CardSkeleton key={i} />
              ))}
            </div>
          ) : searchResults.length === 0 ? (
            <div className="glass-card py-16 flex flex-col items-center justify-center text-center">
              <Search size={32} className="text-[#555555] mb-3" />
              <p className="text-[#888888] text-sm">No jobs found for your query</p>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              variants={stagger}
              initial="hidden"
              animate="show"
            >
              {searchResults.map((job) => (
                <motion.div key={job.id} variants={fadeUp}>
                  <JobCard job={job} />
                </motion.div>
              ))}
            </motion.div>
          )}
        </section>
      )}

      {/* Saved Jobs */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4">Saved Jobs</h2>

        {savedLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : savedJobs.length === 0 ? (
          <div className="glass-card py-16 flex flex-col items-center justify-center text-center">
            <Briefcase size={32} className="text-[#555555] mb-3" />
            <p className="text-[#888888] text-sm">
              {showSearchResults ? 'No saved jobs yet' : 'Search for jobs to get started'}
            </p>
          </div>
        ) : (
          <>
            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              variants={stagger}
              initial="hidden"
              animate="show"
            >
              {savedJobs.map((job) => (
                <motion.div key={job.id} variants={fadeUp}>
                  <JobCard job={job} />
                </motion.div>
              ))}
            </motion.div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-xs rounded-md border border-[#222222] text-[#888888] hover:text-white hover:border-[#444444] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-xs text-[#888888] px-3">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 text-xs rounded-md border border-[#222222] text-[#888888] hover:text-white hover:border-[#444444] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
