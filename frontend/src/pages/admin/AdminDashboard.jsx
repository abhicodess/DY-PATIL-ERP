import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Users, UserCheck, Calendar, ClipboardCheck } from 'lucide-react';

export const AdminDashboard = () => {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['adminSummary'],
    queryFn: async () => {
      const response = await api.get('/dashboard/summary');
      return response.data.data.metrics;
    },
  });

  return (
    <Layout title="Administrator Dashboard" role="admin">
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-32 bg-slate-900 rounded-2xl animate-pulse border border-white/5" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
          Failed to load dashboard metrics. Check backend connection.
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Dashboard Metrics grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-purple-600/20 text-purple-400 p-3 rounded-xl">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Students</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.total_students}</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-blue-600/20 text-blue-400 p-3 rounded-xl">
                <UserCheck className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Faculty</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.total_faculty}</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-green-600/20 text-green-400 p-3 rounded-xl">
                <Calendar className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Today's Lectures</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.sessions_scheduled_today}</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-orange-600/20 text-orange-400 p-3 rounded-xl">
                <ClipboardCheck className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Sessions Logged</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.attendance_logs_today}</span>
              </div>
            </div>
          </div>

          {/* Quick Shortcuts */}
          <div className="glass p-6 rounded-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Quick Management Actions</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <a href="/admin/students" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition">
                Manage Students Profile
              </a>
              <a href="/admin/faculty" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition">
                Manage Faculty Profiles
              </a>
              <a href="/admin/timetable" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition">
                Manage Lecture Timetables
              </a>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};
