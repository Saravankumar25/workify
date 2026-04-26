import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import ProfileForm from '@/components/ProfileForm';
import { motion } from 'framer-motion';
import { Upload, Loader2, Check, X } from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function Profile() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('form');
  const [dragOver, setDragOver] = useState(false);
  const [parsedDiff, setParsedDiff] = useState(null);

  const importMutation = useMutation({
    mutationFn: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return api.post('/profile/import-pdf', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: (res) => setParsedDiff(res.data),
  });

  const confirmMutation = useMutation({
    mutationFn: (parsedData) => api.put('/profile/confirm-import', { parsed_data: parsedData }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      setParsedDiff(null);
    },
  });

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer?.files?.[0] || e.target?.files?.[0];
      if (file && file.type === 'application/pdf') {
        importMutation.mutate(file);
      }
    },
    [importMutation],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => setDragOver(false), []);

  const handleFileSelect = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (file && file.type === 'application/pdf') {
        importMutation.mutate(file);
      }
    },
    [importMutation],
  );

  const tabs = [
    { id: 'form', label: 'Profile Form' },
    { id: 'import', label: 'PDF Import' },
  ];

  const diffFields = parsedDiff?.fields || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Profile</h1>
        <p className="text-[#888888] mt-1">Manage your professional profile</p>
      </div>

      <div className="flex gap-1 border-b border-[#222222]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors relative ${
              activeTab === tab.id
                ? 'text-white'
                : 'text-[#888888] hover:text-white'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <motion.div
                layoutId="profile-tab-indicator"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-white"
              />
            )}
          </button>
        ))}
      </div>

      {activeTab === 'form' && (
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="glass-card p-6"
        >
          <ProfileForm />
        </motion.div>
      )}

      {activeTab === 'import' && (
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="glass-card p-6 space-y-6"
        >
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">Import from Resume</h2>
            <p className="text-sm text-[#888888]">
              Upload a PDF resume and let AI extract your profile data.
            </p>
          </div>

          {!importMutation.isPending && !parsedDiff && (
            <label
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className={`flex flex-col items-center justify-center gap-3 p-12 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                dragOver
                  ? 'border-white bg-[#111111]'
                  : 'border-[#333333] hover:border-[#555555]'
              }`}
            >
              <Upload size={32} className="text-[#888888]" />
              <p className="text-sm text-[#888888] text-center">
                Drop your resume PDF here or{' '}
                <span className="text-white underline">click to upload</span>
              </p>
              <p className="text-xs text-[#555555]">PDF files only, max 10MB</p>
              <input
                type="file"
                accept="application/pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          )}

          {importMutation.isPending && (
            <div className="flex flex-col items-center justify-center gap-3 py-12">
              <Loader2 size={32} className="animate-spin text-white" />
              <p className="text-sm text-[#888888]">Parsing your resume with AI...</p>
            </div>
          )}

          {importMutation.isError && (
            <div className="flex items-center gap-2 p-3 rounded-md bg-[#1a0a0a] border border-[#ef4444]/20">
              <X size={16} className="text-[#ef4444]" />
              <p className="text-sm text-[#ef4444]">
                Failed to parse resume. Please try a different file.
              </p>
            </div>
          )}

          {parsedDiff && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-white">Review Imported Data</h3>

              <div className="border border-[#222222] rounded-lg overflow-hidden">
                <div className="grid grid-cols-3 gap-px bg-[#222222]">
                  <div className="bg-[#0a0a0a] px-4 py-2.5 text-xs font-medium text-[#888888] uppercase tracking-wider">
                    Field
                  </div>
                  <div className="bg-[#0a0a0a] px-4 py-2.5 text-xs font-medium text-[#888888] uppercase tracking-wider">
                    Current
                  </div>
                  <div className="bg-[#0a0a0a] px-4 py-2.5 text-xs font-medium text-[#888888] uppercase tracking-wider">
                    Imported
                  </div>
                </div>

                <div className="divide-y divide-[#222222]">
                  {diffFields.map((row) => {
                    const changed = row.current !== row.imported;
                    return (
                      <div
                        key={row.field}
                        className={`grid grid-cols-3 gap-px ${
                          changed ? 'bg-[#0a1a0a]' : ''
                        }`}
                      >
                        <div className="bg-[#0a0a0a] px-4 py-2.5 text-sm text-white font-medium">
                          {row.field}
                        </div>
                        <div className="bg-[#0a0a0a] px-4 py-2.5 text-sm text-[#888888] truncate">
                          {row.current || '—'}
                        </div>
                        <div
                          className={`bg-[#0a0a0a] px-4 py-2.5 text-sm truncate ${
                            changed ? 'text-[#22c55e]' : 'text-[#888888]'
                          }`}
                        >
                          {row.imported || '—'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => confirmMutation.mutate(parsedDiff.parsed)}
                  disabled={confirmMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-md text-sm font-medium hover:bg-[#e5e5e5] transition-colors disabled:opacity-50"
                >
                  {confirmMutation.isPending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Check size={16} />
                  )}
                  Confirm Import
                </button>
                <button
                  onClick={() => {
                    setParsedDiff(null);
                    importMutation.reset();
                  }}
                  className="flex items-center gap-2 px-4 py-2 border border-[#222222] text-[#888888] rounded-md text-sm hover:text-white hover:border-[#444444] transition-colors"
                >
                  <X size={16} />
                  Cancel
                </button>
              </div>

              {confirmMutation.isSuccess && (
                <p className="text-sm text-[#22c55e]">Profile updated from resume.</p>
              )}
              {confirmMutation.isError && (
                <p className="text-sm text-[#ef4444]">Import failed. Please try again.</p>
              )}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
