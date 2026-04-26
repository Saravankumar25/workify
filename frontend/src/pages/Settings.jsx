import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { signOut } from 'firebase/auth';
import { auth } from '@/firebase';
import useAuth from '@/store/useAuth';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import { Save, Shield, User, LogOut, Loader2 } from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const inputClass =
  'w-full bg-[#0a0a0a] border border-[#222222] rounded-md px-3 py-2 text-white text-sm placeholder-[#444444] focus:outline-none focus:border-[#444444] transition-colors';

function DailyCapSection() {
  const queryClient = useQueryClient();
  const [cap, setCap] = useState(20);

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get('/settings').then((r) => r.data),
  });

  useEffect(() => {
    if (settings?.daily_apply_cap != null) {
      setCap(settings.daily_apply_cap);
    }
  }, [settings]);

  const mutation = useMutation({
    mutationFn: (daily_apply_cap) => api.patch('/settings', { daily_apply_cap }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  });

  return (
    <motion.div variants={fadeUp} className="glass-card p-6 space-y-4">
      <h2 className="text-lg font-semibold text-white">Daily Application Limit</h2>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm text-[#888888]">Applications per day</label>
          <span className="text-sm font-mono text-white bg-[#111111] px-2.5 py-1 rounded">
            {cap}
          </span>
        </div>

        <input
          type="range"
          min={1}
          max={50}
          value={cap}
          onChange={(e) => setCap(Number(e.target.value))}
          className="w-full accent-white"
        />

        <div className="flex items-center justify-between">
          <p className="text-xs text-[#555555]">Hard limit: 50/day</p>
          <button
            onClick={() => mutation.mutate(cap)}
            disabled={mutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-white text-black rounded-md text-sm font-medium hover:bg-[#e5e5e5] transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Save size={14} />
            )}
            Save
          </button>
        </div>

        {mutation.isSuccess && (
          <p className="text-xs text-[#22c55e]">Daily cap updated.</p>
        )}
        {mutation.isError && (
          <p className="text-xs text-[#ef4444]">Failed to update cap.</p>
        )}
      </div>
    </motion.div>
  );
}


function AccountSection() {
  const user = useAuth((s) => s.user);

  const handleSignOut = async () => {
    await signOut(auth);
  };

  return (
    <motion.div variants={fadeUp} className="glass-card p-6 space-y-4">
      <div className="flex items-center gap-2">
        <User size={18} className="text-[#888888]" />
        <h2 className="text-lg font-semibold text-white">Account</h2>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm text-[#888888] mb-1.5">Display Name</label>
          <input
            type="text"
            value={user?.displayName || ''}
            readOnly
            className={inputClass + ' opacity-60 cursor-not-allowed'}
          />
        </div>
        <div>
          <label className="block text-sm text-[#888888] mb-1.5">Email</label>
          <input
            type="email"
            value={user?.email || ''}
            readOnly
            className={inputClass + ' opacity-60 cursor-not-allowed'}
          />
        </div>
      </div>

      <button
        onClick={handleSignOut}
        className="flex items-center gap-2 px-3 py-1.5 border border-[#ef4444]/30 text-[#ef4444] rounded-md text-sm hover:bg-[#1a0a0a] transition-colors"
      >
        <LogOut size={14} />
        Sign Out
      </button>
    </motion.div>
  );
}

function AdminSection() {
  const queryClient = useQueryClient();

  const { data: adminData, isLoading } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: () => api.get('/settings/admin').then((r) => r.data),
  });

  const capMutation = useMutation({
    mutationFn: ({ userId, daily_apply_cap }) =>
      api.patch('/settings/admin/caps', { user_id: userId, daily_apply_cap }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-settings'] }),
  });

  const users = adminData?.users || [];

  return (
    <motion.div variants={fadeUp} className="glass-card p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Shield size={18} className="text-[#f59e0b]" />
        <h2 className="text-lg font-semibold text-white">Admin</h2>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 size={20} className="animate-spin text-[#888888]" />
        </div>
      ) : users.length === 0 ? (
        <p className="text-sm text-[#888888]">No users found.</p>
      ) : (
        <div className="divide-y divide-[#222222]">
          {users.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between py-3 gap-4"
            >
              <div className="min-w-0">
                <p className="text-sm text-white truncate">
                  {u.display_name || u.email}
                </p>
                <p className="text-xs text-[#555555] truncate">{u.email}</p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <input
                  type="number"
                  min={1}
                  max={50}
                  defaultValue={u.daily_apply_cap ?? 20}
                  onBlur={(e) =>
                    capMutation.mutate({
                      userId: u.id,
                      daily_apply_cap: Number(e.target.value),
                    })
                  }
                  className="w-16 bg-[#0a0a0a] border border-[#222222] rounded px-2 py-1 text-white text-sm text-center focus:outline-none focus:border-[#444444]"
                />
                <span className="text-xs text-[#555555]">/day</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {capMutation.isSuccess && (
        <p className="text-xs text-[#22c55e]">User cap updated.</p>
      )}
      {capMutation.isError && (
        <p className="text-xs text-[#ef4444]">Failed to update user cap.</p>
      )}
    </motion.div>
  );
}

export default function Settings() {
  const user = useAuth((s) => s.user);

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get('/settings').then((r) => r.data),
  });

  const isAdmin = settings?.is_admin === true;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-[#888888] mt-1">Manage your preferences and account</p>
      </div>

      <motion.div
        className="space-y-6"
        variants={stagger}
        initial="hidden"
        animate="show"
      >
        <DailyCapSection />
        <AccountSection />
        {isAdmin && <AdminSection />}
      </motion.div>
    </div>
  );
}
