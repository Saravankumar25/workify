import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import Layout from '@/components/Layout';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import JobsSearch from '@/pages/JobsSearch';
import JobDetail from '@/pages/JobDetail';
import Composer from '@/pages/Composer';
import Apply from '@/pages/Apply';
import Applications from '@/pages/Applications';
import Profile from '@/pages/Profile';
import Settings from '@/pages/Settings';
import Logs from '@/pages/Logs';

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />

      {/* Protected */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/jobs" element={<JobsSearch />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/compose/:jobId" element={<Composer />} />
        <Route path="/apply/:applicationId" element={<Apply />} />
        <Route path="/applications" element={<Applications />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/logs" element={<Logs />} />
      </Route>
    </Routes>
  );
}
