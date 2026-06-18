import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Search, Award, Radio } from 'lucide-react';

export const ExamResults = () => {
  const queryClient = useQueryClient();
  const [studentId, setStudentId] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [semester, setSemester] = useState('');

  // Form states for publishing
  const [showPublishForm, setShowPublishForm] = useState(false);
  const [pubSubjectId, setPubSubjectId] = useState('');
  const [pubSem, setPubSem] = useState('I');
  const [pubStatus, setPubStatus] = useState('');

  // Fetch marksheets with filters
  const { data, isLoading } = useQuery({
    queryKey: ['adminMarksheets', studentId, subjectId, semester],
    queryFn: async () => {
      const response = await api.get('/results/marksheet', {
        params: {
          student_id: studentId || undefined,
          subject_id: subjectId || undefined,
          semester: semester || undefined,
        },
      });
      return response.data;
    },
  });

  // Publish results mutation
  const publishMutation = useMutation({
    mutationFn: async (payload) => {
      await api.post('/results/publish', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['adminMarksheets']);
      setPubStatus('Results published successfully');
      setTimeout(() => setPubStatus(''), 3000);
      setShowPublishForm(false);
    },
    onError: () => {
      setPubStatus('Failed to publish results');
      setTimeout(() => setPubStatus(''), 3000);
    },
  });

  const handlePublish = (e) => {
    e.preventDefault();
    if (!pubSubjectId || !pubSem) return;
    publishMutation.mutate({
      subject_id: Number(pubSubjectId),
      semester: pubSem,
    });
  };

  return (
    <Layout title="Exam Evaluation Logs" role="admin">
      <div className="flex flex-col gap-6">
        {/* Actions header */}
        <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-3 items-center">
            <input
              type="text"
              placeholder="Filter by Student ID..."
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 w-44"
            />

            <input
              type="text"
              placeholder="Filter by Subject ID..."
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 w-44"
            />

            <select
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              <option value="">All Semesters</option>
              {['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'].map((sem) => (
                <option key={sem} value={sem}>Sem {sem}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowPublishForm(!showPublishForm)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-xl transition font-semibold text-sm"
          >
            Publish Results
          </button>
        </div>

        {/* Publish message status */}
        {pubStatus && (
          <div className={`p-4 rounded-xl border text-sm text-center font-bold ${
            pubStatus.includes('successfully')
              ? 'bg-green-500/10 border-green-500/20 text-green-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}>
            {pubStatus}
          </div>
        )}

        {/* Modal / Inline form to publish */}
        {showPublishForm && (
          <div className="glass p-6 rounded-2xl border border-purple-500/20 max-w-lg">
            <h3 className="text-lg font-bold text-white mb-4">Publish Grades Sheet</h3>
            <form onSubmit={handlePublish} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Subject ID</label>
                <input
                  type="number"
                  required
                  value={pubSubjectId}
                  onChange={(e) => setPubSubjectId(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200"
                  placeholder="e.g. 1"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Semester</label>
                <select
                  value={pubSem}
                  onChange={(e) => setPubSem(e.target.value)}
                  className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-300"
                >
                  {['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'].map((sem) => (
                    <option key={sem} value={sem}>Semester {sem}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2 mt-2">
                <button type="submit" className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-semibold transition">
                  Confirm & Publish
                </button>
                <button type="button" onClick={() => setShowPublishForm(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-semibold transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Marksheet table grid */}
        <div className="glass rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 font-semibold">
                  <th className="p-4">Student</th>
                  <th className="p-4">Roll</th>
                  <th className="p-4">Subject</th>
                  <th className="p-4">Semester</th>
                  <th className="p-4">Internal Marks</th>
                  <th className="p-4">External Marks</th>
                  <th className="p-4">Total</th>
                  <th className="p-4">Grade</th>
                  <th className="p-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [1, 2, 3].map((n) => (
                    <tr key={n} className="border-b border-white/5 animate-pulse">
                      <td colSpan={9} className="p-4"><div className="h-4 bg-slate-800 rounded w-full" /></td>
                    </tr>
                  ))
                ) : data?.data?.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="p-8 text-center text-slate-500">No marks records found.</td>
                  </tr>
                ) : (
                  data?.data?.map((record) => (
                    <tr key={record.id} className="border-b border-white/5 hover:bg-white/[0.02] transition">
                      <td className="p-4 text-white font-bold">{record.student_name}</td>
                      <td className="p-4 text-slate-300">{record.roll_no}</td>
                      <td className="p-4 text-slate-200">{record.subject_name} ({record.subject_code})</td>
                      <td className="p-4 text-slate-400">Sem {record.semester}</td>
                      <td className="p-4 text-slate-300">{record.internal_marks}</td>
                      <td className="p-4 text-slate-300">{record.external_marks}</td>
                      <td className="p-4 text-slate-200 font-semibold">{record.total}</td>
                      <td className="p-4">
                        <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold">
                          {record.grade}
                        </span>
                      </td>
                      <td className="p-4 text-center">
                        {record.is_published ? (
                          <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded font-semibold">
                            Published
                          </span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded font-semibold">
                            Draft
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
};
