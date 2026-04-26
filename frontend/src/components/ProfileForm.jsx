import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Save, Loader2 } from 'lucide-react';

export default function ProfileForm() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    full_name: '',
    location: '',
    phone: '',
    email: '',
    linkedin_url: '',
    portfolio_url: '',
    linkedin_email: '',
    linkedin_password: '',
    summary: '',
    skills: '',
    experience_json: '[]',
    education_json: '[]',
    projects_json: '[]',
    certifications_json: '[]',
    languages: '',
  });

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then((r) => r.data),
  });

  useEffect(() => {
    if (profile) {
      setForm({
        full_name: profile.full_name || '',
        location: profile.location || '',
        phone: profile.phone || '',
        email: profile.email || '',
        linkedin_url: profile.linkedin_url || '',
        portfolio_url: profile.portfolio_url || '',
        linkedin_email: profile.linkedin_email || '',
        linkedin_password: profile.linkedin_password || '',
        summary: profile.summary || '',
        skills: (profile.skills || []).join(', '),
        experience_json: profile.experience_json || '[]',
        education_json: profile.education_json || '[]',
        projects_json: profile.projects_json || '[]',
        certifications_json: profile.certifications_json || '[]',
        languages: (profile.languages || []).join(', '),
      });
    }
  }, [profile]);

  const mutation = useMutation({
    mutationFn: (data) => api.put('/profile', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  });

  const handleSave = () => {
    const payload = {
      ...form,
      skills: form.skills.split(',').map((s) => s.trim()).filter(Boolean),
      languages: form.languages.split(',').map((s) => s.trim()).filter(Boolean),
    };
    mutation.mutate(payload);
  };

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-[#888888]" size={24} />
      </div>
    );
  }

  const inputClass =
    'w-full bg-[#0a0a0a] border border-[#222222] rounded-md px-3 py-2 text-white text-sm placeholder-[#444444] focus:outline-none focus:border-[#444444] transition-colors';

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { label: 'Full Name', field: 'full_name', placeholder: 'John Doe' },
          { label: 'Email', field: 'email', placeholder: 'john@example.com' },
          { label: 'Phone', field: 'phone', placeholder: '+1 234 567 8900' },
          { label: 'Location', field: 'location', placeholder: 'San Francisco, CA' },
          { label: 'LinkedIn URL', field: 'linkedin_url', placeholder: 'https://linkedin.com/in/...' },
          { label: 'Portfolio URL', field: 'portfolio_url', placeholder: 'https://...' },
        ].map(({ label, field, placeholder }) => (
          <div key={field}>
            <label className="block text-sm text-[#888888] mb-1.5">{label}</label>
            <input
              type="text"
              value={form[field]}
              onChange={handleChange(field)}
              placeholder={placeholder}
              className={inputClass}
            />
          </div>
        ))}
      </div>

      <div className="border border-[#1a1a1a] rounded-lg p-4 space-y-3">
        <p className="text-sm font-medium text-white">LinkedIn Login Credentials</p>
        <p className="text-xs text-[#555555]">Used by the auto-apply bot to log into LinkedIn on your behalf.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-[#888888] mb-1.5">LinkedIn Email</label>
            <input
              type="email"
              value={form.linkedin_email}
              onChange={handleChange('linkedin_email')}
              placeholder="you@example.com"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm text-[#888888] mb-1.5">LinkedIn Password</label>
            <input
              type="password"
              value={form.linkedin_password}
              onChange={handleChange('linkedin_password')}
              placeholder="••••••••"
              className={inputClass}
            />
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm text-[#888888] mb-1.5">Summary</label>
        <textarea
          value={form.summary}
          onChange={handleChange('summary')}
          placeholder="Brief professional summary..."
          rows={4}
          className={inputClass + ' resize-y'}
        />
      </div>

      <div>
        <label className="block text-sm text-[#888888] mb-1.5">Skills (comma-separated)</label>
        <input
          type="text"
          value={form.skills}
          onChange={handleChange('skills')}
          placeholder="React, Python, AWS, ..."
          className={inputClass}
        />
      </div>

      <div>
        <label className="block text-sm text-[#888888] mb-1.5">Languages (comma-separated)</label>
        <input
          type="text"
          value={form.languages}
          onChange={handleChange('languages')}
          placeholder="English, Spanish, ..."
          className={inputClass}
        />
      </div>

      {[
        { label: 'Experience (JSON)', field: 'experience_json', hint: '[{"title":"...", "company":"...", "start":"...", "end":"...", "bullets":["..."]}]' },
        { label: 'Education (JSON)', field: 'education_json', hint: '[{"degree":"...", "institution":"...", "year":"...", "gpa":"..."}]' },
        { label: 'Projects (JSON)', field: 'projects_json', hint: '[{"name":"...", "url":"...", "description":"...", "tech":["..."]}]' },
        { label: 'Certifications (JSON)', field: 'certifications_json', hint: '[{"name":"...", "issuer":"...", "year":"..."}]' },
      ].map(({ label, field, hint }) => (
        <div key={field}>
          <label className="block text-sm text-[#888888] mb-1.5">{label}</label>
          <textarea
            value={form[field]}
            onChange={handleChange(field)}
            rows={3}
            className={inputClass + ' font-mono text-xs resize-y'}
          />
          <p className="text-xs text-[#444444] mt-1">{hint}</p>
        </div>
      ))}

      <button
        onClick={handleSave}
        disabled={mutation.isPending}
        className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-md text-sm font-medium hover:bg-[#e5e5e5] transition-colors disabled:opacity-50"
      >
        {mutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
        Save Profile
      </button>

      {mutation.isSuccess && (
        <p className="text-sm text-[#22c55e]">Profile saved successfully.</p>
      )}
      {mutation.isError && (
        <p className="text-sm text-[#ef4444]">Failed to save profile. Please try again.</p>
      )}
    </div>
  );
}
