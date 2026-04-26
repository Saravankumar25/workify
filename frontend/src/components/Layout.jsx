import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { signOut } from 'firebase/auth';
import { auth } from '@/firebase';
import useAuth from '@/store/useAuth';
import {
  LayoutDashboard,
  Search,
  FolderKanban,
  User,
  Settings,
  ScrollText,
  LogOut,
  Briefcase,
} from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/jobs', icon: Search, label: 'Jobs' },
  { to: '/applications', icon: FolderKanban, label: 'Tracker' },
  { to: '/profile', icon: User, label: 'Profile' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/logs', icon: ScrollText, label: 'Logs' },
];

export default function Layout() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSignOut = async () => {
    await signOut(auth);
    navigate('/');
  };

  return (
    <div className="flex h-screen bg-black">
      {/* Sidebar */}
      <aside className="w-60 border-r border-[#222222] flex flex-col">
        <div className="p-5 border-b border-[#222222]">
          <div className="flex items-center gap-2">
            <Briefcase size={20} className="text-white" />
            <span className="text-white font-semibold text-lg tracking-tight">Workify</span>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-[#111111] text-white'
                    : 'text-[#888888] hover:text-white hover:bg-[#0a0a0a]'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-[#222222]">
          <div className="flex items-center gap-3 px-3 py-2 mb-2">
            {user?.photoURL ? (
              <img
                src={user.photoURL}
                alt=""
                className="w-7 h-7 rounded-full"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-[#222222] flex items-center justify-center text-xs text-[#888888]">
                {(user?.displayName || user?.email || '?')[0].toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">
                {user?.displayName || 'User'}
              </p>
              <p className="text-xs text-[#888888] truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-md text-sm text-[#888888] hover:text-white hover:bg-[#0a0a0a] transition-colors"
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
