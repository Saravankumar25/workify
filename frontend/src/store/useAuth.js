import { create } from 'zustand';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '@/firebase';
import api from '@/lib/api';

/**
 * Auth store.
 *
 * Contract for ProtectedRoute & data-fetching pages:
 *  - `loading` stays `true` until we've BOTH resolved the Firebase auth
 *    state AND (if signed in) successfully upserted the Mongo User doc via
 *    POST /auth/sync. Rendering protected pages before /auth/sync lands
 *    causes a race where backend endpoints return 404 "User not found"
 *    because Beanie has no record for the uid yet. Don't loosen this.
 *  - `synced` is a UI hint — true once /auth/sync has succeeded at least
 *    once during the current session.
 *  - `syncError` surfaces the failure message when /auth/sync repeatedly
 *    fails, so the UI can show something actionable instead of flapping.
 */
const useAuth = create((set, get) => ({
  user: null,
  loading: true,
  synced: false,
  syncError: null,
  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),
  setSynced: (synced) => set({ synced }),
  setSyncError: (syncError) => set({ syncError }),
  reset: () =>
    set({ user: null, loading: false, synced: false, syncError: null }),
}));

async function syncWithBackend(attempt = 0) {
  try {
    await api.post('/auth/sync');
    return { ok: true };
  } catch (err) {
    // Cold-start + DNS warmup + Firebase token fetch can take a moment on
    // the first request. Retry twice with gentle backoff before we give up.
    if (attempt < 2) {
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
      return syncWithBackend(attempt + 1);
    }
    const detail =
      err?.response?.data?.detail || err?.message || 'Unknown sync failure';
    return { ok: false, detail };
  }
}

onAuthStateChanged(auth, async (firebaseUser) => {
  const store = useAuth.getState();
  store.setLoading(true);
  store.setSyncError(null);

  if (!firebaseUser) {
    store.setUser(null);
    store.setSynced(false);
    store.setLoading(false);
    return;
  }

  // Set the user THEN sync. Crucially, loading stays `true` until sync
  // resolves — so ProtectedRoute still shows the spinner and does not
  // mount data-fetching pages that would 404 before the Mongo user exists.
  store.setUser(firebaseUser);
  const res = await syncWithBackend();
  if (res.ok) {
    store.setSynced(true);
  } else {
    store.setSynced(false);
    store.setSyncError(res.detail);
    // Log once for diagnostics — visible in browser console.
    console.error('[auth] /auth/sync failed after retries:', res.detail);
  }
  store.setLoading(false);
});

export default useAuth;
