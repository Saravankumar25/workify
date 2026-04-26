import { Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import useAuth from '@/store/useAuth';

export function ProtectedRoute({ children }) {
  const { user, loading, synced, syncError } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-[#888888] animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Signed in but /auth/sync repeatedly failed — don't mount data-fetching
  // pages that will just 404. Show an explicit message so the user can
  // recover (refresh / retry).
  if (!synced) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center px-6">
        <div className="glass-card max-w-md w-full p-6 text-center">
          <p className="text-white font-medium mb-2">
            Can't reach the Workify server
          </p>
          <p className="text-sm text-[#888888] mb-4">
            {syncError ||
              'We signed you in with Firebase, but the backend is not responding. Please retry.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-white text-black rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-200 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return children;
}
