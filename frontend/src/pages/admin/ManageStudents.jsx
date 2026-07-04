import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Trash2, Search, Plus } from 'lucide-react';

export const ManageStudents = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [dept, setDept] = useState('');
  const [year, setYear] = useState('');
  const [div, setDiv] = useState('');

  // Fetch student records with filters
  const { data, isLoading } = useQuery({
    queryKey: ['studentsList', search, dept, year, div],
    queryFn: async () => {
      const response = await api.get('/students', {
        params: { search, dept, year, division: div },
      });
      return response.data;
    },
  });

  // Soft delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      await api.delete(`/students/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['studentsList']);
    },
  });

  const handleDelete = (id, name) => {
    if (window.confirm(`Are you sure you want to soft delete student: ${name}?`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <Layout title="Student Management" role="admin">
      <div className="flex flex-col gap-6">
        {/* Filters and search */}
        <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name, roll, PRN..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl pl-10 pr-4 py-2 w-full text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
          </div>

          <select
            value={dept}
            onChange={(e) => setDept(e.target.value)}
            className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="">All Departments</option>
            <option value="CS">CS</option>
            <option value="IT">IT</option>
            <option value="AIML">AIML</option>
            <option value="AIDS">AIDS</option>
          </select>

          <select
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="">All Years</option>
            <option value="I">I Year</option>
            <option value="II">II Year</option>
            <option value="III">III Year</option>
            <option value="IV">IV Year</option>
          </select>

          <select
            value={div}
            onChange={(e) => setDiv(e.target.value)}
            className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
          >
            <option value="">All Divisions</option>
            <option value="A">Div A</option>
            <option value="B">Div B</option>
            <option value="C">Div C</option>
            <option value="D">Div D</option>
          </select>
        </div>

        {/* Student Records List */}
        <div className="glass rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 font-semibold">
                  <th className="p-4">Roll No</th>
                  <th className="p-4">PRN</th>
                  <th className="p-4">Name</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Year/Div</th>
                  <th className="p-4">Email</th>
                  <th className="p-4">Mobile</th>
                  <th className="p-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [1, 2, 3].map((n) => (
                    <tr key={n} className="border-b border-white/5 animate-pulse">
                      <td colSpan={8} className="p-4"><div className="h-4 bg-slate-800 rounded w-full" /></td>
                    </tr>
                  ))
                ) : data?.data?.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-slate-500">No student records found.</td>
                  </tr>
                ) : (
                  data?.data?.map((student) => (
                    <tr key={student.id} className="border-b border-white/5 hover:bg-white/[0.02] transition">
                      <td className="p-4 text-slate-200 font-semibold">{student.roll}</td>
                      <td className="p-4 text-slate-300">{student.prn}</td>
                      <td className="p-4 text-white font-bold">{student.name}</td>
                      <td className="p-4 text-slate-400">{student.department}</td>
                      <td className="p-4 text-slate-400">{student.year} - {student.division}</td>
                      <td className="p-4 text-slate-400">{student.email}</td>
                      <td className="p-4 text-slate-400">{student.contact_number || '-'}</td>
                      <td className="p-4 text-center">
                        <button
                          onClick={() => handleDelete(student.id, student.name)}
                          className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-xl transition"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
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
