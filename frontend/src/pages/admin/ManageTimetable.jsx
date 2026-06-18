import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/authService';
import { Layout } from '../../components/Layout';
import { Trash2, Plus, Edit3 } from 'lucide-react';

export const ManageTimetable = () => {
  const queryClient = useQueryClient();
  const [day, setDay] = useState('Monday');
  const [division, setDivision] = useState('');
  const [branch, setBranch] = useState('');
  const [year, setYear] = useState('');

  // Form states for new slot
  const [showAddForm, setShowAddForm] = useState(false);
  const [formDay, setFormDay] = useState('Monday');
  const [formTime, setFormTime] = useState('09:00-10:00');
  const [formStartTime, setFormStartTime] = useState('09:00:00');
  const [formEndTime, setFormEndTime] = useState('10:00:00');
  const [formSubject, setFormSubject] = useState('');
  const [formTeacher, setFormTeacher] = useState('');
  const [formRoom, setFormRoom] = useState('');
  const [formDiv, setFormDiv] = useState('A');
  const [formBranch, setFormBranch] = useState('CS');
  const [formYear, setFormYear] = useState('I');
  const [formSem, setFormSem] = useState('I');

  // Fetch timetable slots with filters
  const { data, isLoading } = useQuery({
    queryKey: ['timetableList', day, division, branch, year],
    queryFn: async () => {
      const response = await api.get('/timetable', {
        params: { day, division, branch, year, per_page: 50 },
      });
      return response.data;
    },
  });

  // Create slot mutation
  const createMutation = useMutation({
    mutationFn: async (payload) => {
      await api.post('/timetable', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['timetableList']);
      setShowAddForm(false);
      // Reset form
      setFormSubject('');
      setFormTeacher('');
      setFormRoom('');
    },
  });

  // Delete slot mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      await api.delete(`/timetable/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['timetableList']);
    },
  });

  const handleDelete = (id, subject) => {
    if (window.confirm(`Are you sure you want to delete slot for subject: ${subject}?`)) {
      deleteMutation.mutate(id);
    }
  };

  const handleAddSlot = (e) => {
    e.preventDefault();
    createMutation.mutate({
      day: formDay,
      time: formTime,
      start_time: formStartTime,
      end_time: formEndTime,
      subject: formSubject,
      teacher: formTeacher,
      room: formRoom,
      division: formDiv,
      branch: formBranch,
      year: formYear,
      semester: formSem,
      slot_type: 'Theory',
    });
  };

  return (
    <Layout title="Timetable Manager" role="admin">
      <div className="flex flex-col gap-6">
        {/* Filter bar + Add trigger */}
        <div className="glass p-6 rounded-2xl flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-3 items-center">
            <select
              value={day}
              onChange={(e) => setDay(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>

            <select
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              <option value="">All Branches</option>
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
              value={division}
              onChange={(e) => setDivision(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:ring-1 focus:ring-purple-500"
            >
              <option value="">All Divisions</option>
              <option value="A">Div A</option>
              <option value="B">Div B</option>
              <option value="C">Div C</option>
              <option value="D">Div D</option>
            </select>
          </div>

          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-xl transition font-semibold flex items-center gap-2 text-sm"
          >
            <Plus className="h-4 w-4" />
            Add Slot
          </button>
        </div>

        {/* Modal / Form to Add Slot */}
        {showAddForm && (
          <div className="glass p-6 rounded-2xl border border-purple-500/20">
            <h3 className="text-lg font-bold text-white mb-4">Add Timetable Slot</h3>
            <form onSubmit={handleAddSlot} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Day</label>
                <select value={formDay} onChange={(e) => setFormDay(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm">
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Time Label</label>
                <input type="text" value={formTime} onChange={(e) => setFormTime(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="09:00-10:00" />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Start Time</label>
                <input type="text" value={formStartTime} onChange={(e) => setFormStartTime(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="09:00:00" />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">End Time</label>
                <input type="text" value={formEndTime} onChange={(e) => setFormEndTime(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="10:00:00" />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Subject Name</label>
                <input type="text" required value={formSubject} onChange={(e) => setFormSubject(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="e.g. Database Systems" />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Teacher</label>
                <input type="text" value={formTeacher} onChange={(e) => setFormTeacher(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="Faculty Name" />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Room</label>
                <input type="text" value={formRoom} onChange={(e) => setFormRoom(e.target.value)} className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 w-full text-sm text-slate-200" placeholder="e.g. 302-A" />
              </div>

              <div className="flex items-end gap-2">
                <button type="submit" className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-semibold transition">
                  Save Slot
                </button>
                <button type="button" onClick={() => setShowAddForm(false)} className="w-full py-2 bg-slate-800 hover:bg-slate-755 text-slate-300 rounded-xl text-sm font-semibold transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Timetable Listings */}
        <div className="glass rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 font-semibold">
                  <th className="p-4">Time</th>
                  <th className="p-4">Subject</th>
                  <th className="p-4">Teacher</th>
                  <th className="p-4">Class Division</th>
                  <th className="p-4">Branch</th>
                  <th className="p-4">Room</th>
                  <th className="p-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [1, 2, 3].map((n) => (
                    <tr key={n} className="border-b border-white/5 animate-pulse">
                      <td colSpan={7} className="p-4"><div className="h-4 bg-slate-800 rounded w-full" /></td>
                    </tr>
                  ))
                ) : data?.data?.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">No timetable entries found.</td>
                  </tr>
                ) : (
                  data?.data?.map((slot) => (
                    <tr key={slot.id} className="border-b border-white/5 hover:bg-white/[0.02] transition">
                      <td className="p-4 text-slate-200 font-semibold">{slot.time}</td>
                      <td className="p-4 text-white font-bold">{slot.subject}</td>
                      <td className="p-4 text-slate-300">{slot.teacher || 'N/A'}</td>
                      <td className="p-4 text-slate-400">{slot.year} - {slot.division}</td>
                      <td className="p-4 text-slate-400">{slot.branch}</td>
                      <td className="p-4 text-slate-400">{slot.room}</td>
                      <td className="p-4 text-center">
                        <button
                          onClick={() => handleDelete(slot.id, slot.subject)}
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
