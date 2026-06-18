import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Award } from 'lucide-react';

export const MyResults = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['studentResultsList'],
    queryFn: async () => {
      const response = await api.get('/student/results');
      return response.data.data;
    },
  });

  return (
    <Layout title="My Academic Results" role="student">
      {isLoading ? (
        <div className="space-y-4 animate-pulse">
          {[1, 2].map((n) => (
            <div key={n} className="h-20 bg-slate-900 rounded-2xl border border-white/5" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-6 rounded-2xl">
          Failed to load results. Check backend connection.
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="glass p-6 rounded-2xl">
            <h3 className="text-xl font-bold text-white mb-2">Evaluated Semester Grades</h3>
            <p className="text-slate-400 text-sm">Official marksheets published by university controllers.</p>
          </div>

          {data?.length === 0 ? (
            <div className="glass p-8 text-center text-slate-500 rounded-2xl">
              No academic results have been published for you yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {data?.map((res) => (
                <div key={res.id} className="glass p-6 rounded-2xl flex justify-between items-center relative overflow-hidden">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-purple-400 font-semibold uppercase tracking-wider">
                      Sem {res.semester}
                    </span>
                    <h4 className="text-lg font-bold text-white leading-tight">{res.subject_name}</h4>
                    <p className="text-xs text-slate-400 mt-1">Code: {res.subject_code}</p>
                    <div className="flex items-center gap-4 text-xs text-slate-400 mt-2 border-t border-white/5 pt-2">
                      <span>Internal: {res.internal_marks}</span>
                      <span>External: {res.external_marks}</span>
                      <span className="font-bold text-slate-300">Total: {res.total}</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-center justify-center bg-purple-500/10 text-purple-400 rounded-xl px-4 py-3 border border-purple-500/20">
                    <span className="text-xs text-slate-500 uppercase font-semibold">Grade</span>
                    <span className="text-2xl font-black">{res.grade}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Layout>
  );
};
