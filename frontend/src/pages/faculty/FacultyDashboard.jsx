import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Calendar, BookOpen, Clock, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export const FacultyDashboard = () => {
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['facultySummary'],
    queryFn: async () => {
      const response = await api.get('/dashboard/summary');
      return response.data.data.metrics;
    },
  });

  return (
    <Layout title="Faculty Dashboard" role="faculty">
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((n) => (
            <div key={n} className="h-32 bg-slate-900 rounded-2xl animate-pulse border border-white/5" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
          Failed to load dashboard metrics. Check backend connection.
        </div>
      ) : (
        <div className="flex flex-col gap-8">
          {/* Faculty Dashboard Metrics grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-purple-600/20 text-purple-400 p-3 rounded-xl">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Today's Lectures</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.today_sessions}</span>
              </div>
            </div>

            <div className="glass p-6 rounded-2xl flex items-center gap-4">
              <div className="bg-blue-600/20 text-blue-400 p-3 rounded-xl">
                <BookOpen className="h-6 w-6" />
              </div>
              <div>
                <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider block">Assigned Subjects</span>
                <span className="text-3xl font-extrabold text-white mt-1 block">{summary.total_subjects}</span>
              </div>
            </div>
          </div>

          {/* Quick Shortcuts */}
          <div className="flex flex-col md:flex-row gap-6">
            {/* Recent Sessions list */}
            <div className="glass p-6 rounded-2xl flex-1">
              <h3 className="text-xl font-bold text-white mb-4">Recent Sessions Logged</h3>
              {summary.recent_sessions?.length === 0 ? (
                <p className="text-slate-400">No attendance sessions logged recently.</p>
              ) : (
                <div className="space-y-3">
                  {summary.recent_sessions?.map((session) => (
                    <div key={session.id} className="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
                      <div>
                        <h4 className="font-semibold text-slate-200">{session.subject}</h4>
                        <p className="text-xs text-slate-400">Div {session.division} • {session.date}</p>
                      </div>
                      <span className="text-xs font-bold uppercase text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                        {session.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions bar */}
            <div className="glass p-6 rounded-2xl md:w-80 flex flex-col gap-4">
              <h3 className="text-xl font-bold text-white mb-2">Shortcuts</h3>
              <Link to="/faculty/attendance" className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-center font-semibold transition shadow-lg shadow-purple-600/10 hover:shadow-purple-600/25">
                Mark Lecture Attendance
              </Link>
              <Link to="/faculty/timetable" className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-center font-semibold transition">
                View Timetable
              </Link>
              <Link to="/faculty/results" className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-center font-semibold transition">
                Upload Semester Results
              </Link>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};
