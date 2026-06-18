import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Award, BookOpen, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

export const StudentDashboard = () => {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['studentSummary'],
    queryFn: async () => {
      const response = await api.get('/dashboard/summary');
      return response.data.data.metrics;
    },
  });

  return (
    <Layout title="Student Portal Dashboard" role="student">
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-32 bg-slate-900 rounded-2xl animate-pulse border border-white/5" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
          Failed to load dashboard metrics. Check backend connection.
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Student Dashboard Metrics grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-purple-600/20 text-purple-400 p-3 rounded-xl">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Attendance Rate</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.attendance_percentage}%</span>
                <span className="text-xs text-slate-500 mt-1 block">{summary.classes_attended} / {summary.total_classes} classes</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-blue-600/20 text-blue-400 p-3 rounded-xl">
                <Award className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Published Grades</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.published_results}</span>
                <span className="text-xs text-slate-500 mt-1 block">Subjects evaluated</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-green-600/20 text-green-400 p-3 rounded-xl">
                <BookOpen className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Today's Lectures</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.today_lectures}</span>
                <span className="text-xs text-slate-500 mt-1 block">Scheduled timetable slots</span>
              </div>
            </div>
          </div>

          {/* Quick Shortcuts */}
          <div className="glass p-6 rounded-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Portal Modules</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Link to="/student/attendance" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition font-semibold">
                My Attendance Logs
              </Link>
              <Link to="/student/results" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition font-semibold">
                My Marksheet / Grades
              </Link>
              <Link to="/student/timetable" className="p-4 bg-slate-900/50 hover:bg-slate-900 border border-white/5 rounded-xl text-center text-slate-300 hover:text-white transition font-semibold">
                My Class Timetable
              </Link>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};
