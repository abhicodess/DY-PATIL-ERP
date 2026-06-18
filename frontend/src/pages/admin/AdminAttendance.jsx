import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Search, AlertTriangle } from 'lucide-react';

export const AdminAttendance = () => {
  const [activeTab, setActiveTab] = useState('records'); // records, defaulters
  const [search, setSearch] = useState('');
  const [dept, setDept] = useState('');
  const [year, setYear] = useState('');
  const [threshold, setThreshold] = useState(75);

  // 1. Fetch general attendance records
  const { data: recordsData, isLoading: loadingRecords } = useQuery({
    queryKey: ['adminAttendanceRecords', search, dept, year],
    queryFn: async () => {
      const response = await api.get('/attendance', {
        params: { search, dept, year },
      });
      return response.data;
    },
    enabled: activeTab === 'records',
  });

  // 2. Fetch defaulters
  const { data: defaultersData, isLoading: loadingDefaulters } = useQuery({
    queryKey: ['adminDefaulters', dept, year, threshold],
    queryFn: async () => {
      const response = await api.get('/attendance/defaulters', {
        params: { dept, year, threshold },
      });
      return response.data;
    },
    enabled: activeTab === 'defaulters',
  });

  return (
    <Layout title="Attendance Overview" role="admin">
      <div className="flex flex-col gap-6">
        {/* Navigation Tabs */}
        <div className="flex border-b border-white/10 gap-4">
          <button
            onClick={() => setActiveTab('records')}
            className={`pb-3 text-sm font-semibold transition ${
              activeTab === 'records'
                ? 'border-b-2 border-purple-500 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Attendance Logs
          </button>
          <button
            onClick={() => setActiveTab('defaulters')}
            className={`pb-3 text-sm font-semibold transition flex items-center gap-2 ${
              activeTab === 'defaulters'
                ? 'border-b-2 border-purple-500 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            Defaulter Alerts
          </button>
        </div>

        {/* Tab 1: Attendance Logs */}
        {activeTab === 'records' && (
          <div className="flex flex-col gap-6">
            {/* Filters */}
            <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center">
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search by student name or subject..."
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
            </div>

            {/* List */}
            <div className="glass rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 font-semibold">
                      <th className="p-4">Date</th>
                      <th className="p-4">Student</th>
                      <th className="p-4">Roll</th>
                      <th className="p-4">Subject</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Class</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingRecords ? (
                      [1, 2, 3].map((n) => (
                        <tr key={n} className="border-b border-white/5 animate-pulse">
                          <td colSpan={6} className="p-4"><div className="h-4 bg-slate-800 rounded w-full" /></td>
                        </tr>
                      ))
                    ) : recordsData?.data?.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-slate-500">No attendance logs found.</td>
                      </tr>
                    ) : (
                      recordsData?.data?.map((record) => (
                        <tr key={record.id} className="border-b border-white/5 hover:bg-white/[0.02] transition">
                          <td className="p-4 text-slate-300">{record.date}</td>
                          <td className="p-4 text-white font-bold">{record.student_name}</td>
                          <td className="p-4 text-slate-400">{record.roll_no}</td>
                          <td className="p-4 text-slate-200">{record.subject}</td>
                          <td className="p-4">
                            <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                              record.status === 'Present'
                                ? 'bg-green-500/20 text-green-400 border border-green-500/20'
                                : 'bg-red-500/20 text-red-400 border border-red-500/20'
                            }`}>
                              {record.status}
                            </span>
                          </td>
                          <td className="p-4 text-slate-400">{record.year} - {record.division} ({record.dept})</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Defaulter Alerts */}
        {activeTab === 'defaulters' && (
          <div className="flex flex-col gap-6">
            {/* Filters */}
            <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-300">Defaulter Threshold (%):</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-20 text-sm text-center text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
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
            </div>

            {/* List */}
            <div className="glass rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 font-semibold">
                      <th className="p-4">Student</th>
                      <th className="p-4">Roll</th>
                      <th className="p-4">Department</th>
                      <th className="p-4">Year/Div</th>
                      <th className="p-4">Attendance Stats</th>
                      <th className="p-4 text-center">Alert Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingDefaulters ? (
                      [1, 2, 3].map((n) => (
                        <tr key={n} className="border-b border-white/5 animate-pulse">
                          <td colSpan={6} className="p-4"><div className="h-4 bg-slate-800 rounded w-full" /></td>
                        </tr>
                      ))
                    ) : defaultersData?.data?.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-slate-500">No students are below the specified threshold.</td>
                      </tr>
                    ) : (
                      defaultersData?.data?.map((student, idx) => (
                        <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.02] transition">
                          <td className="p-4 text-white font-bold">{student.student_name || 'N/A'}</td>
                          <td className="p-4 text-slate-300">{student.roll_no || student.roll || 'N/A'}</td>
                          <td className="p-4 text-slate-400">{student.department || student.dept || 'N/A'}</td>
                          <td className="p-4 text-slate-400">{student.year || 'N/A'} - {student.division || 'N/A'}</td>
                          <td className="p-4 text-slate-200">
                            {student.percentage || student.attendance_pct || 0}% ({student.present || student.present_count || 0} / {student.total || student.total_lectures || 0} classes)
                          </td>
                          <td className="p-4 text-center">
                            <span className="px-2.5 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-semibold inline-flex items-center gap-1">
                              Critical Warning
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
