import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { ClipboardCheck } from 'lucide-react';

export const MyAttendance = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['studentAttendanceDetails'],
    queryFn: async () => {
      const response = await api.get('/student/attendance');
      return response.data.data;
    },
  });

  return (
    <Layout title="My Attendance Records" role="student">
      {isLoading ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-32 bg-slate-900 rounded-2xl border border-white/5" />
          <div className="h-64 bg-slate-900 rounded-2xl border border-white/5" />
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
          Failed to load attendance logs. Check backend connection.
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Summary Row */}
          <div className="glass p-6 rounded-2xl flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white mb-1">Cumulative Attendance</h3>
              <p className="text-slate-400 text-sm">
                Attended {data.overall.present} out of {data.overall.total} total lectures
              </p>
            </div>
            <div className="bg-purple-600/20 text-purple-400 px-4 py-2 rounded-2xl border border-purple-500/20">
              <span className="text-2xl font-black">{data.overall.percentage}%</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Subject Ratios */}
            <div className="glass p-6 rounded-2xl">
              <h4 className="font-bold text-white text-lg mb-4">Subject-wise Breakdown</h4>
              <div className="space-y-4">
                {data.subjects?.map((sub, idx) => (
                  <div key={idx} className="flex flex-col gap-1.5">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-slate-300 font-semibold">{sub.subject}</span>
                      <span className="text-purple-400 font-bold">{sub.percentage}% ({sub.present}/{sub.total})</span>
                    </div>
                    {/* Progress Bar */}
                    <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-white/5">
                      <div
                        className={`h-full rounded-full ${
                          sub.percentage >= 75 ? 'bg-purple-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${sub.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* History logs */}
            <div className="glass p-6 rounded-2xl">
              <h4 className="font-bold text-white text-lg mb-4">Lecture Logs History</h4>
              {data.history?.length === 0 ? (
                <p className="text-slate-500">No attendance logs logged yet.</p>
              ) : (
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                  {data.history?.map((log) => (
                    <div key={log.id} className="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
                      <div>
                        <h5 className="font-semibold text-slate-200 text-sm">{log.subject}</h5>
                        <p className="text-xs text-slate-400">{log.date}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                        log.status === 'Present'
                          ? 'bg-green-500/20 text-green-400 border border-green-500/20'
                          : 'bg-red-500/20 text-red-400 border border-red-500/20'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};
