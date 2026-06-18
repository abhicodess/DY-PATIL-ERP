import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Award, Plus, Trash2 } from 'lucide-react';

export const UploadResults = () => {
  const [subjectId, setSubjectId] = useState('');
  const [semester, setSemester] = useState('I');
  const [records, setRecords] = useState([{ student_id: '', internal_marks: '', external_marks: '' }]);
  const [statusMsg, setStatusMsg] = useState('');

  // Bulk submit mutation
  const uploadMutation = useMutation({
    mutationFn: async (payload) => {
      const response = await api.post('/results/bulk', payload);
      return response.data;
    },
    onSuccess: (data) => {
      setStatusMsg(`Successfully submitted ${data.data.submitted_records} results.`);
      setRecords([{ student_id: '', internal_marks: '', external_marks: '' }]);
      setSubjectId('');
    },
    onError: (err) => {
      setStatusMsg(err.response?.data?.error?.message || 'Failed to submit results. Check input formats.');
    },
  });

  const handleAddRow = () => {
    setRecords((prev) => [...prev, { student_id: '', internal_marks: '', external_marks: '' }]);
  };

  const handleRemoveRow = (idx) => {
    setRecords((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleRowChange = (idx, field, val) => {
    setRecords((prev) =>
      prev.map((r, i) => {
        if (i === idx) {
          return { ...r, [field]: val };
        }
        return r;
      })
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!subjectId || !semester) return;

    // Filter out rows missing student_id or marks
    const validRecords = records
      .filter((r) => r.student_id && r.internal_marks !== '' && r.external_marks !== '')
      .map((r) => ({
        student_id: Number(r.student_id),
        internal_marks: Number(r.internal_marks),
        external_marks: Number(r.external_marks),
      }));

    if (validRecords.length === 0) {
      setStatusMsg('No valid student grade records to submit.');
      return;
    }

    uploadMutation.mutate({
      subject_id: Number(subjectId),
      semester,
      records: validRecords,
    });
  };

  return (
    <Layout title="Marks Upload Desk" role="faculty">
      <div className="flex flex-col gap-6 max-w-4xl">
        <div className="glass p-6 rounded-2xl">
          <h3 className="text-xl font-bold text-white mb-2">Bulk Marks Sheet Submission</h3>
          <p className="text-slate-400 text-sm">Enter internal and external evaluations below.</p>
        </div>

        {statusMsg && (
          <div className={`p-4 rounded-xl text-center text-sm font-bold border ${
            statusMsg.includes('Successfully')
              ? 'bg-green-500/10 border-green-500/20 text-green-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}>
            {statusMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="glass p-6 rounded-2xl flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Subject ID</label>
              <input
                type="number"
                required
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 w-full"
                placeholder="e.g. 5"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">Semester</label>
              <select
                value={semester}
                onChange={(e) => setSemester(e.target.value)}
                className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500 w-full"
              >
                {['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'].map((sem) => (
                  <option key={sem} value={sem}>Semester {sem}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="border-t border-white/5 pt-4">
            <h4 className="font-bold text-white text-base mb-4">Student Grade Entries</h4>

            <div className="space-y-3">
              {records.map((rec, idx) => (
                <div key={idx} className="flex gap-4 items-center">
                  <div className="flex-1">
                    <input
                      type="number"
                      placeholder="Student ID"
                      value={rec.student_id}
                      onChange={(e) => handleRowChange(idx, 'student_id', e.target.value)}
                      className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-sm w-full text-slate-200"
                    />
                  </div>
                  <div className="w-36">
                    <input
                      type="number"
                      placeholder="Internal Marks"
                      value={rec.internal_marks}
                      onChange={(e) => handleRowChange(idx, 'internal_marks', e.target.value)}
                      className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-sm w-full text-slate-200"
                    />
                  </div>
                  <div className="w-36">
                    <input
                      type="number"
                      placeholder="External Marks"
                      value={rec.external_marks}
                      onChange={(e) => handleRowChange(idx, 'external_marks', e.target.value)}
                      className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-sm w-full text-slate-200"
                    />
                  </div>
                  {records.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveRow(idx)}
                      className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={handleAddRow}
              className="mt-4 flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 font-semibold transition"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Student Entry
            </button>
          </div>

          <button
            type="submit"
            disabled={uploadMutation.isPending}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-2.5 rounded-xl transition mt-2 flex items-center justify-center gap-2"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Confirm Submission'}
          </button>
        </form>
      </div>
    </Layout>
  );
};
